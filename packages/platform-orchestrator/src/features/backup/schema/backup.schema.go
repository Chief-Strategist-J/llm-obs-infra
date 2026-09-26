/*
Package schema defines data entities and transfer contracts for database disaster recovery and volume purging.

ALGORITHM BLUEPRINT:
1. BackupOptions: Captures execution flags for database dumps and volume deletion.
2. BackupReport: Captures resulting file paths, timestamp metadata, and operation outcomes.
3. Invariants:
   - Automated backups write SQL dumps into workspace 'backups/' directory with ISO timestamps.
   - Purge actions default to safety checks, stopping containers before volume deletion.
*/
package schema

type BackupOptions struct {
	BackupOnly bool   `json:"backupOnly"`
	Purge      bool   `json:"purge"`
	TargetDir  string `json:"targetDir"`
}

type BackupReport struct {
	Success            bool   `json:"success"`
	AlloyDBDumpFile    string `json:"alloyDbDumpFile,omitempty"`
	ClickHouseDumpFile string `json:"clickHouseDumpFile,omitempty"`
	VolumesPurged      bool   `json:"volumesPurged"`
	Message            string `json:"message"`
}
