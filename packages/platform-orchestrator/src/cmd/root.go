/*
Package cmd provides the primary Cobra CLI interface and execution wiring for the platform orchestrator.

ALGORITHM BLUEPRINT:
1. RootCommand: Initializes top-level 'llmobs' CLI, base path resolution, and dependency injection wiring.
2. Subcommand Registration:
   - up: Dispatches to StackService.StartStack with resolved profiles and cert verification.
   - down: Dispatches to StackService.StopStack.
   - restart: Dispatches to StackService.RestartStack.
   - status: Dispatches to StackService.GetStatus and renders a tabular overview.
   - scale: Supports both interactive prompting and direct arguments (service scaling or simulated compute node launches).
   - health: Dispatches to HealthService.RunHealthChecks; renders concurrent latency metrics and health states.
   - certs: Dispatches to CertService.EnsureCertificates; generates self-signed TLS certs without openssl dependency.
   - ports: Dispatches to PortService.FreePorts; detects and cleans socket contention.
   - server: Boots the HTTP REST API server on configured port (default 31499).
3. Invariants:
   - Root execution resolves workspace path automatically.
   - Cobra commands return non-zero exit codes upon service failure.
*/
package cmd

import (
	"context"
	"fmt"
	"net/http"
	"os"
	"path/filepath"
	"strconv"
	"time"

	"github.com/spf13/cobra"

	"github.com/llm-observability/platform/packages/platform-orchestrator/src/api/rest"
	certsSchema "github.com/llm-observability/platform/packages/platform-orchestrator/src/features/certs/schema"
	certsService "github.com/llm-observability/platform/packages/platform-orchestrator/src/features/certs/services"
	healthSchema "github.com/llm-observability/platform/packages/platform-orchestrator/src/features/health/schema"
	healthService "github.com/llm-observability/platform/packages/platform-orchestrator/src/features/health/services"
	portsService "github.com/llm-observability/platform/packages/platform-orchestrator/src/features/ports/services"
	scaleSchema "github.com/llm-observability/platform/packages/platform-orchestrator/src/features/scale/schema"
	scaleService "github.com/llm-observability/platform/packages/platform-orchestrator/src/features/scale/services"
	stackSchema "github.com/llm-observability/platform/packages/platform-orchestrator/src/features/stack/schema"
	stackService "github.com/llm-observability/platform/packages/platform-orchestrator/src/features/stack/services"
	"github.com/llm-observability/platform/packages/platform-orchestrator/src/infra/docker"
	"github.com/llm-observability/platform/packages/platform-orchestrator/src/infra/observability"
)

func findWorkspaceRoot() string {
	dir, err := os.Getwd()
	if err != nil {
		return "."
	}
	for {
		if _, err := os.Stat(filepath.Join(dir, "docker-compose.yml")); err == nil {
			return dir
		}
		parent := filepath.Dir(dir)
		if parent == dir {
			break
		}
		dir = parent
	}
	return "."
}

func Execute() {
	workspaceRoot := findWorkspaceRoot()

	tracer := observability.NewOTelTracerAdapter("llmobs-orchestrator")
	dockerAdapter := docker.NewDockerAdapter(workspaceRoot)

	stackSvc := stackService.NewStackService(dockerAdapter, dockerAdapter, tracer, workspaceRoot)
	scaleSvc := scaleService.NewScaleService(dockerAdapter, tracer, workspaceRoot)
	healthSvc := healthService.NewHealthService(tracer)
	certsSvc := certsService.NewCertService(tracer)
	portSvc := portsService.NewPortService(dockerAdapter, tracer)

	restHandler := rest.NewOrchestratorHandler(stackSvc, scaleSvc, healthSvc, certsSvc, workspaceRoot)

	rootCmd := &cobra.Command{
		Use:   "llmobs",
		Short: "LLMObs Infrastructure Platform Orchestrator CLI",
		Long:  "Open-standard, unified Go orchestration engine for LLM Observability & Infrastructure Platform.",
	}

	upCmd := &cobra.Command{
		Use:   "up [profiles...]",
		Short: "Start infrastructure stack with profiles",
		RunE: func(cmd *cobra.Command, args []string) error {
			ctx := context.Background()

			certSpec := certsSchema.DefaultCertSpec(workspaceRoot)
			_, _ = certsSvc.EnsureCertificates(ctx, certSpec)

			_ = portSvc.FreePorts(ctx, nil)

			outcome, err := stackSvc.StartStack(ctx, stackSchema.StackUpCommand{
				Profiles: args,
				Detach:   true,
			})
			if err != nil {
				return err
			}
			fmt.Printf("✓ %s (Profiles: %v)\n", outcome.Message, outcome.ActiveServices)
			return nil
		},
	}

	downCmd := &cobra.Command{
		Use:   "down",
		Short: "Stop infrastructure stack across all profiles",
		RunE: func(cmd *cobra.Command, args []string) error {
			outcome, err := stackSvc.StopStack(context.Background())
			if err != nil {
				return err
			}
			fmt.Println("✓", outcome.Message)
			return nil
		},
	}

	restartCmd := &cobra.Command{
		Use:   "restart [profiles...]",
		Short: "Restart infrastructure stack",
		RunE: func(cmd *cobra.Command, args []string) error {
			outcome, err := stackSvc.RestartStack(context.Background(), args)
			if err != nil {
				return err
			}
			fmt.Printf("✓ %s (Profiles: %v)\n", outcome.Message, outcome.ActiveServices)
			return nil
		},
	}

	statusCmd := &cobra.Command{
		Use:   "status",
		Short: "Display active container statuses",
		RunE: func(cmd *cobra.Command, args []string) error {
			statuses, err := stackSvc.GetStatus(context.Background())
			if err != nil {
				return err
			}
			fmt.Printf("%-35s %-20s %-25s %s\n", "NAME", "SERVICE", "STATUS", "PORTS")
			fmt.Println("---------------------------------------------------------------------------------------------------------")
			for _, s := range statuses {
				fmt.Printf("%-35s %-20s %-25s %s\n", s.Name, s.Service, s.Status, s.Ports)
			}
			return nil
		},
	}

	scaleCmd := &cobra.Command{
		Use:   "scale [service <name> <replicas> | node <id> [host] | list | down-node <id>]",
		Short: "Scale stateless services or simulated compute nodes",
		RunE: func(cmd *cobra.Command, args []string) error {
			ctx := context.Background()

			if len(args) == 0 {
				fmt.Println("Select scaling mode:")
				fmt.Println("  1) Scale a specific stateless service (e.g. llmobs-temporal)")
				fmt.Println("  2) Launch an additional simulated compute node (Node 2, 3...)")
				fmt.Println("  3) List active scaled containers")
				fmt.Println("  4) Stop a simulated compute node")
				fmt.Print("Enter choice [1-4]: ")
				var choice int
				fmt.Scanln(&choice)

				switch choice {
				case 1:
					fmt.Print("Enter service name [default: llmobs-temporal]: ")
					var svc string
					fmt.Scanln(&svc)
					if svc == "" {
						svc = "llmobs-temporal"
					}
					fmt.Print("Enter replica count [e.g. 2, 3]: ")
					var count int
					fmt.Scanln(&count)
					if count < 1 {
						count = 2
					}
					err := scaleSvc.ScaleService(ctx, scaleSchema.ScaleServiceCommand{Service: svc, Replicas: count})
					if err != nil {
						return err
					}
					fmt.Printf("✓ Scaled '%s' to %d replicas.\n", svc, count)
				case 2:
					fmt.Print("Enter simulated compute node ID [default: 2]: ")
					var nodeID int
					fmt.Scanln(&nodeID)
					if nodeID < 2 {
						nodeID = 2
					}
					fmt.Print("Enter Primary Data Host IP [default: host.docker.internal]: ")
					var host string
					fmt.Scanln(&host)
					if host == "" {
						host = "host.docker.internal"
					}
					meta, err := scaleSvc.LaunchComputeNode(ctx, scaleSchema.LaunchNodeCommand{
						NodeID:          nodeID,
						PrimaryDataHost: host,
					})
					if err != nil {
						return err
					}
					fmt.Printf("✓ Launched Compute Node %d under project '%s' (Data Host: %s)\n", meta.NodeID, meta.ProjectName, meta.PrimaryDataHost)
				case 3:
					containers, err := scaleSvc.ListActiveContainers(ctx)
					if err != nil {
						return err
					}
					for _, c := range containers {
						fmt.Printf("%-35s %-20s %s\n", c.Name, c.Status, c.Ports)
					}
				case 4:
					fmt.Print("Enter compute node ID to terminate [e.g. 2]: ")
					var nodeID int
					fmt.Scanln(&nodeID)
					if nodeID < 2 {
						nodeID = 2
					}
					if err := scaleSvc.TerminateComputeNode(ctx, nodeID); err != nil {
						return err
					}
					fmt.Printf("✓ Terminated compute node %d.\n", nodeID)
				}
				return nil
			}

			subcmd := args[0]
			switch subcmd {
			case "service":
				if len(args) < 3 {
					return fmt.Errorf("usage: llmobs scale service <service_name> <replicas>")
				}
				rep, err := strconv.Atoi(args[2])
				if err != nil {
					return err
				}
				if err := scaleSvc.ScaleService(ctx, scaleSchema.ScaleServiceCommand{Service: args[1], Replicas: rep}); err != nil {
					return err
				}
				fmt.Printf("✓ Scaled service '%s' to %d replicas.\n", args[1], rep)
			case "node":
				nodeID := 2
				if len(args) >= 2 {
					var err error
					nodeID, err = strconv.Atoi(args[1])
					if err != nil {
						return err
					}
				}
				host := "host.docker.internal"
				if len(args) >= 3 {
					host = args[2]
				}
				meta, err := scaleSvc.LaunchComputeNode(ctx, scaleSchema.LaunchNodeCommand{
					NodeID:          nodeID,
					PrimaryDataHost: host,
				})
				if err != nil {
					return err
				}
				fmt.Printf("✓ Launched simulated compute node %d under project '%s'\n", meta.NodeID, meta.ProjectName)
			case "down-node":
				if len(args) < 2 {
					return fmt.Errorf("usage: llmobs scale down-node <node_id>")
				}
				nodeID, err := strconv.Atoi(args[1])
				if err != nil {
					return err
				}
				if err := scaleSvc.TerminateComputeNode(ctx, nodeID); err != nil {
					return err
				}
				fmt.Printf("✓ Terminated compute node %d.\n", nodeID)
			case "list":
				containers, err := scaleSvc.ListActiveContainers(ctx)
				if err != nil {
					return err
				}
				for _, c := range containers {
					fmt.Printf("%-35s %-20s %s\n", c.Name, c.Status, c.Ports)
				}
			default:
				if len(args) >= 2 {
					rep, err := strconv.Atoi(args[1])
					if err == nil {
						return scaleSvc.ScaleService(ctx, scaleSchema.ScaleServiceCommand{Service: args[0], Replicas: rep})
					}
				}
				return fmt.Errorf("unknown scale command: %s", subcmd)
			}
			return nil
		},
	}

	healthCmd := &cobra.Command{
		Use:   "health [primaryHost]",
		Short: "Run concurrent diagnostic health checks across all services",
		RunE: func(cmd *cobra.Command, args []string) error {
			host := "localhost"
			if len(args) > 0 {
				host = args[0]
			}
			targets := healthSchema.DefaultHealthTargets(host)
			report := healthSvc.RunHealthChecks(context.Background(), targets)

			fmt.Println("=========================================================================")
			fmt.Printf(" Platform Health Verification (Checked: %d, Healthy: %d)\n", report.CheckedCount, report.HealthyCount)
			fmt.Println("=========================================================================")
			fmt.Printf("%-20s %-25s %-12s %s\n", "SERVICE", "ENDPOINT", "STATUS", "LATENCY")
			fmt.Println("-------------------------------------------------------------------------")
			for _, r := range report.Results {
				fmt.Printf("%-20s %-25s %-12s %.1fms\n", r.Service, r.Target, r.Status, r.LatencyMs)
			}
			fmt.Println("=========================================================================")
			if !report.Healthy {
				return fmt.Errorf("one or more required services failed health checks")
			}
			fmt.Println("✓ All required platform endpoints are operational.")
			return nil
		},
	}

	certsCmd := &cobra.Command{
		Use:   "certs",
		Short: "Generate self-signed TLS certificates natively in Go",
		RunE: func(cmd *cobra.Command, args []string) error {
			spec := certsSchema.DefaultCertSpec(workspaceRoot)
			res, err := certsSvc.EnsureCertificates(context.Background(), spec)
			if err != nil {
				return err
			}
			if res.Generated {
				fmt.Printf("✓ Generated new TLS certificates at %s\n", res.CertPath)
			} else {
				fmt.Printf("✓ Existing valid TLS certificates verified at %s\n", res.CertPath)
			}
			return nil
		},
	}

	serverCmd := &cobra.Command{
		Use:   "server",
		Short: "Start REST API daemon conforming to OpenAPI specification",
		RunE: func(cmd *cobra.Command, args []string) error {
			router := rest.NewRouter(restHandler)
			port := 31499
			srv := &http.Server{
				Addr:         fmt.Sprintf(":%d", port),
				Handler:      router,
				ReadTimeout:  15 * time.Second,
				WriteTimeout: 60 * time.Second,
			}
			fmt.Printf("⚡ Platform Orchestrator REST API listening on http://localhost:%d/api/v1\n", port)
			return srv.ListenAndServe()
		},
	}

	rootCmd.AddCommand(upCmd, downCmd, restartCmd, statusCmd, scaleCmd, healthCmd, certsCmd, serverCmd)

	if err := rootCmd.Execute(); err != nil {
		os.Exit(1)
	}
}
