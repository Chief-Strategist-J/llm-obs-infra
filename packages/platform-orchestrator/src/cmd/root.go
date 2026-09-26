/*
Package cmd provides the primary Cobra CLI interface and execution wiring for the platform orchestrator.

ALGORITHM BLUEPRINT:
1. RootCommand: Initializes top-level 'llmobs' CLI, base path resolution, and dependency injection wiring.
2. Subcommand Registration:
   - up: Interactive stack profile selector (TTY) or direct argument resolution; executes pre-flight checks, TLS certs, port checks, and stack startup.
   - down: Shuts down all infrastructure containers across all profiles.
   - restart: Restarts stack services and triggers automated post-boot health verification.
   - status: Renders tabular overview of all managed container statuses.
   - logs: Follows container log streams.
   - free-ports: Scans and terminates stale socket listeners blocking platform ports.
   - scale: Supports interactive and argument-driven scaling of services or simulated compute nodes.
   - health: Executes concurrent TCP and HTTP diagnostic probes across platform services.
   - certs: Generates native Go X.509 certificates for CA, server, and client.
   - backup-purge: Performs disaster recovery dumps for AlloyDB and ClickHouse; optionally purges volumes.
   - setup: Executes end-to-end 7-step platform bootstrapping pipeline.
   - cloudflare: Manages Cloudflare Tunnel token configuration and container lifecycle.
   - gdpr-erasure: Performs GDPR/CCPA data erasure across analytical and relational stores with audit logging.
   - verify-credentials: Runs domain service credential verification test suites.
   - server: Boots REST API daemon conforming to OpenAPI 3.1.0 specification.
3. Invariants:
   - Root execution resolves workspace path automatically.
   - Zero inline comments inside function bodies.
   - Cobra commands return non-zero exit codes upon failure.
*/
package cmd

import (
	"bufio"
	"context"
	"fmt"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"github.com/spf13/cobra"

	"github.com/llm-observability/platform/packages/platform-orchestrator/src/api/rest"
	backupSchema "github.com/llm-observability/platform/packages/platform-orchestrator/src/features/backup/schema"
	backupService "github.com/llm-observability/platform/packages/platform-orchestrator/src/features/backup/services"
	certsSchema "github.com/llm-observability/platform/packages/platform-orchestrator/src/features/certs/schema"
	certsService "github.com/llm-observability/platform/packages/platform-orchestrator/src/features/certs/services"
	cloudflareService "github.com/llm-observability/platform/packages/platform-orchestrator/src/features/cloudflare/services"
	gdprSchema "github.com/llm-observability/platform/packages/platform-orchestrator/src/features/gdpr/schema"
	gdprService "github.com/llm-observability/platform/packages/platform-orchestrator/src/features/gdpr/services"
	healthSchema "github.com/llm-observability/platform/packages/platform-orchestrator/src/features/health/schema"
	healthService "github.com/llm-observability/platform/packages/platform-orchestrator/src/features/health/services"
	portsService "github.com/llm-observability/platform/packages/platform-orchestrator/src/features/ports/services"
	prereqsService "github.com/llm-observability/platform/packages/platform-orchestrator/src/features/prereqs/services"
	scaleSchema "github.com/llm-observability/platform/packages/platform-orchestrator/src/features/scale/schema"
	scaleService "github.com/llm-observability/platform/packages/platform-orchestrator/src/features/scale/services"
	setupService "github.com/llm-observability/platform/packages/platform-orchestrator/src/features/setup/services"
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

func promptInteractiveProfile() []string {
	fileInfo, _ := os.Stdin.Stat()
	if (fileInfo.Mode() & os.ModeCharDevice) == 0 {
		return []string{"full"}
	}

	fmt.Println("\n=====================================================")
	fmt.Println("  LLM Observability Infrastructure Stack Selector    ")
	fmt.Println("=====================================================")
	fmt.Println("Select the infrastructure stack profile you want to launch:")
	fmt.Println()
	fmt.Println("  [1] Full Stack      - All 10 services (Default)")
	fmt.Println("  [2] Database Stack  - AlloyDB (PostgreSQL) + Redis Ledger")
	fmt.Println("  [3] Analytics Stack - ClickHouse Analytics DB")
	fmt.Println("  [4] Streaming Stack - Apache Kafka Event Broker")
	fmt.Println("  [5] Workflows Engine- Temporal Engine (+ auto-includes Database dependency)")
	fmt.Println("  [6] Tracing Stack   - Tempo + OpenTelemetry Collector + Grafana UI")
	fmt.Println("  [7] Network Gateway - Traefik Gateway + Service Registry")
	fmt.Println("  [8] Stateful Plane  - Dedicated Data Tier (AlloyDB, Kafka, Redis, ClickHouse, Tempo)")
	fmt.Println("  [9] Stateless Plane - Autoscaled Compute/Edge (Traefik, Registry, OTel, Grafana, Temporal)")
	fmt.Println("  [10] Custom Profiles- Specify custom profiles (e.g. 'stateful' or 'stateless')")
	fmt.Println("-----------------------------------------------------")
	fmt.Print("Enter choice [1-10] (default: 1): ")

	reader := bufio.NewReader(os.Stdin)
	choice, _ := reader.ReadString('\n')
	choice = strings.TrimSpace(choice)

	switch choice {
	case "2":
		return []string{"db"}
	case "3":
		return []string{"analytics"}
	case "4":
		return []string{"streaming"}
	case "5":
		return []string{"workflows"}
	case "6":
		return []string{"tracing"}
	case "7":
		return []string{"network"}
	case "8":
		return []string{"stateful"}
	case "9":
		return []string{"stateless"}
	case "10":
		fmt.Print("Enter profiles separated by space (e.g. db streaming): ")
		custom, _ := reader.ReadString('\n')
		custom = strings.TrimSpace(custom)
		if custom == "" {
			return []string{"full"}
		}
		return strings.Fields(custom)
	default:
		return []string{"full"}
	}
}

func Execute() {
	workspaceRoot := findWorkspaceRoot()

	tracer := observability.NewOTelTracerAdapter("llmobs-orchestrator")
	dockerAdapter := docker.NewDockerAdapter(workspaceRoot)

	prereqSvc := prereqsService.NewPrereqService(tracer)
	certsSvc := certsService.NewCertService(tracer)
	portSvc := portsService.NewPortService(dockerAdapter, tracer)
	stackSvc := stackService.NewStackService(dockerAdapter, dockerAdapter, tracer, workspaceRoot)
	scaleSvc := scaleService.NewScaleService(dockerAdapter, tracer, workspaceRoot)
	healthSvc := healthService.NewHealthService(tracer)
	backupSvc := backupService.NewBackupService(dockerAdapter, tracer, workspaceRoot)
	cloudflareSvc := cloudflareService.NewCloudflareService(dockerAdapter, tracer, workspaceRoot)
	gdprSvc := gdprService.NewGDPRService(tracer, workspaceRoot)
	setupSvc := setupService.NewSetupService(prereqSvc, certsSvc, tracer, workspaceRoot)

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

			profiles := args
			if len(profiles) == 0 {
				profiles = promptInteractiveProfile()
			}

			certSpec := certsSchema.DefaultCertSpec(workspaceRoot)
			_, _ = certsSvc.EnsureCertificates(ctx, certSpec)

			_ = portSvc.FreePorts(ctx, nil)

			outcome, err := stackSvc.StartStack(ctx, stackSchema.StackUpCommand{
				Profiles: profiles,
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
			ctx := context.Background()
			outcome, err := stackSvc.RestartStack(ctx, args)
			if err != nil {
				return err
			}
			fmt.Printf("✓ %s (Profiles: %v)\n", outcome.Message, outcome.ActiveServices)

			fmt.Println("\nRunning post-restart health check...")
			targets := healthSchema.DefaultHealthTargets("localhost")
			_ = healthSvc.RunHealthChecks(ctx, targets)

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

	logsCmd := &cobra.Command{
		Use:   "logs [services...]",
		Short: "Stream container logs",
		RunE: func(cmd *cobra.Command, args []string) error {
			tail, _ := cmd.Flags().GetInt("tail")
			if tail == 0 {
				tail = 100
			}
			return stackSvc.StreamLogs(context.Background(), tail)
		},
	}
	logsCmd.Flags().IntP("tail", "n", 100, "Number of lines to show from end of logs")

	freePortsCmd := &cobra.Command{
		Use:   "free-ports",
		Short: "Clean up conflicting host ports",
		RunE: func(cmd *cobra.Command, args []string) error {
			ctx := context.Background()
			if err := portSvc.FreePorts(ctx, nil); err != nil {
				return err
			}
			fmt.Println("✓ Platform ports verified and ready.")
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

	backupPurgeCmd := &cobra.Command{
		Use:   "backup-purge",
		Short: "Perform database disaster recovery backup and optional volume purge",
		RunE: func(cmd *cobra.Command, args []string) error {
			backupOnly, _ := cmd.Flags().GetBool("backup-only")
			opts := backupSchema.BackupOptions{
				BackupOnly: backupOnly,
				Purge:      !backupOnly,
			}
			report, err := backupSvc.ExecuteBackupAndPurge(context.Background(), opts)
			if err != nil {
				return err
			}
			if report.AlloyDBDumpFile != "" {
				fmt.Printf("✓ AlloyDB backup saved to: %s\n", report.AlloyDBDumpFile)
			}
			if report.ClickHouseDumpFile != "" {
				fmt.Printf("✓ ClickHouse schema & partition freeze saved to: %s\n", report.ClickHouseDumpFile)
			}
			fmt.Printf("✓ %s\n", report.Message)
			return nil
		},
	}
	backupPurgeCmd.Flags().Bool("backup-only", false, "Only dump databases without purging Docker volumes")

	setupCmd := &cobra.Command{
		Use:   "setup",
		Short: "Run full 7-step platform bootstrapping pipeline",
		RunE: func(cmd *cobra.Command, args []string) error {
			pull, _ := cmd.Flags().GetBool("pull")
			report, err := setupSvc.RunSetupPipeline(context.Background(), pull)
			for _, st := range report.Steps {
				if st.Passed {
					fmt.Printf("  ✓ [%d/7] %s (%v)\n", st.Index, st.Name, st.Duration.Round(time.Millisecond))
				} else {
					fmt.Printf("  ✖ [%d/7] %s - ERROR: %s\n", st.Index, st.Name, st.Error)
				}
			}
			if err != nil {
				return err
			}
			fmt.Printf("\n✓ %s (%d/%d steps passed)\n", report.Message, report.PassedSteps, report.TotalSteps)
			return nil
		},
	}
	setupCmd.Flags().Bool("pull", false, "Pull Docker images during setup")

	cloudflareCmd := &cobra.Command{
		Use:   "cloudflare [setup|start|stop|status|logs]",
		Short: "Manage Cloudflare Tunnel ingress",
		RunE: func(cmd *cobra.Command, args []string) error {
			ctx := context.Background()
			action := "setup"
			if len(args) > 0 {
				action = args[0]
			}

			switch action {
			case "setup":
				fmt.Print("Enter your Cloudflare Tunnel Token: ")
				reader := bufio.NewReader(os.Stdin)
				token, _ := reader.ReadString('\n')
				token = strings.TrimSpace(token)
				if token == "" {
					return fmt.Errorf("tunnel token cannot be empty")
				}
				if err := cloudflareSvc.SaveTunnelToken(token); err != nil {
					return err
				}
				fmt.Println("✓ Saved Cloudflare Tunnel Token to .env")
				rep, err := cloudflareSvc.StartTunnel(ctx)
				if err != nil {
					return err
				}
				fmt.Println("✓", rep.Message)
			case "start":
				rep, err := cloudflareSvc.StartTunnel(ctx)
				if err != nil {
					return err
				}
				fmt.Println("✓", rep.Message)
			case "stop":
				rep, err := cloudflareSvc.StopTunnel(ctx)
				if err != nil {
					return err
				}
				fmt.Println("✓", rep.Message)
			case "status":
				st, err := cloudflareSvc.GetStatus(ctx)
				if err != nil {
					return err
				}
				fmt.Println(st)
			case "logs":
				return cloudflareSvc.StreamLogs(ctx)
			default:
				return fmt.Errorf("unknown cloudflare action: %s", action)
			}
			return nil
		},
	}

	gdprCmd := &cobra.Command{
		Use:   "gdpr-erasure",
		Short: "Execute GDPR/CCPA right-to-erasure across databases",
		RunE: func(cmd *cobra.Command, args []string) error {
			userID, _ := cmd.Flags().GetString("user-id")
			customerID, _ := cmd.Flags().GetString("customer-id")
			if userID == "" && customerID == "" {
				return fmt.Errorf("must provide --user-id or --customer-id")
			}
			report, err := gdprSvc.ExecuteErasure(context.Background(), gdprSchema.ErasureRequest{
				UserID:     userID,
				CustomerID: customerID,
			})
			if err != nil {
				return err
			}
			fmt.Printf("✓ %s (ClickHouse: %v, AlloyDB: %v, Audit: %v)\n", report.Message, report.ClickHousePurged, report.AlloyDBPurged, report.AuditRecorded)
			return nil
		},
	}
	gdprCmd.Flags().String("user-id", "", "Target User ID for erasure")
	gdprCmd.Flags().String("customer-id", "", "Target Customer ID for erasure")

	verifyCmd := &cobra.Command{
		Use:   "verify-credentials [service]",
		Short: "Verify credentials for local microservices",
		RunE: func(cmd *cobra.Command, args []string) error {
			service := "auth"
			if len(args) > 0 {
				service = args[0]
			}
			scriptPath := filepath.Join(workspaceRoot, "local-services", service, "scripts", "verify-credentials.sh")
			if _, err := os.Stat(scriptPath); err != nil {
				pyScript := filepath.Join(workspaceRoot, "local-services", service, "scripts", "verify-credentials.py")
				if _, errPy := os.Stat(pyScript); errPy == nil {
					pyCmd := exec.Command("python3", append([]string{pyScript}, args[1:]...)...)
					pyCmd.Dir = filepath.Dir(pyScript)
					pyCmd.Stdout = os.Stdout
					pyCmd.Stderr = os.Stderr
					return pyCmd.Run()
				}
				return fmt.Errorf("verify-credentials script not found for service '%s'", service)
			}
			shCmd := exec.Command("bash", append([]string{scriptPath}, args[1:]...)...)
			shCmd.Dir = filepath.Dir(scriptPath)
			shCmd.Stdout = os.Stdout
			shCmd.Stderr = os.Stderr
			return shCmd.Run()
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

	rootCmd.AddCommand(
		upCmd,
		downCmd,
		restartCmd,
		statusCmd,
		logsCmd,
		freePortsCmd,
		scaleCmd,
		healthCmd,
		certsCmd,
		backupPurgeCmd,
		setupCmd,
		cloudflareCmd,
		gdprCmd,
		verifyCmd,
		serverCmd,
	)

	if err := rootCmd.Execute(); err != nil {
		os.Exit(1)
	}
}
