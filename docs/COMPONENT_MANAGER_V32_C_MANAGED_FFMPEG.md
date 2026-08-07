# Component Manager v32-C Managed FFmpeg Boundary

## Purpose

v32-C turns FFmpeg into a managed local component boundary while preserving external detection as a separate read-only path.

The application now distinguishes:

- external FFmpeg/FFprobe detected on the machine
- managed FFmpeg/FFprobe controlled by the application
- missing, partial, corrupt, incompatible, and ready states
- managed health failures that require repair

## Implemented Model

### Component identity

The boundary is implemented as one managed bundle with two executables:

- `ffmpeg`
- `ffprobe`

The installation record is managed as a single activation unit, while health checks validate both binaries.

### Installation types

- `managed`
- `externally_detected`

Managed installs may be activated, repaired, removed, and relocated under the component root.

External installs are read-only:

- never moved
- never removed by the app
- never repaired automatically
- never written into PATH

## Location Policy

Managed FFmpeg lives under the application-controlled components root, using a versioned directory layout.

The active path is resolved internally by the component manager. The app does not require:

- PATH
- administrator privileges
- manual copying into technical folders
- global environment changes

## Local Install Boundary

Because the HTTP downloader is not part of v32-C, managed installation only accepts local sources:

- a local directory
- a local ZIP package
- a test fixture

The install flow is:

1. receive local source
2. validate the source type
3. extract or copy to staging
4. reject traversal, absolute paths, symlinks, and archive bombs
5. validate `ffmpeg.exe` and `ffprobe.exe`
6. run a health check in staging
7. activate the staged directory atomically
8. persist installation metadata
9. clean staging

No arbitrary installer execution is allowed.
No shell-based extraction is used.

## Health Check

The health checker validates:

- both binaries exist
- both binaries are files
- both binaries can execute
- version output is parseable when possible
- ffprobe can inspect a small local fixture
- ffmpeg can run a minimal no-output probe

Health states include:

- `ready`
- `ready_with_warnings`
- `partial`
- `corrupt`
- `probe_failed`
- `executable_failed`
- `timed_out`
- `unavailable`

## Resolution Policy

Central resolution prefers:

1. managed active and healthy
2. explicit external preference
3. discovered external and healthy
4. unavailable

The media locator delegates to this central policy instead of maintaining a separate source of truth.

## Repair And Removal

Managed installs can be repaired only from a local source already available to the application.

Repair is staged first and only removes the previous active files after the replacement is verified.

Removal:

- is allowed for managed installs
- is blocked while the component is in use
- falls back to external detection when available

Removal of external installs is forbidden.

## Integration Points

v32-C is wired into:

- `MediaToolLocator`
- `AudioPreparationService`
- `MediaInspectionService`
- `VisualAnalysisService`
- `ClipRenderService`
- `TranscriptionCapabilityResolver`
- component-manager CLI commands

## Security Constraints

- no network download path
- no PATH mutation
- no hidden install
- no arbitrary `.exe` installer execution
- no extraction outside staging
- no symlink extraction
- no archive traversal
- no archive bombs beyond bounded limits
- no permanent MP4 retention change

## Limitations

- no HTTP downloader
- no remote update flow
- no onboarding flow
- no package-manager integration
- no global PATH management
- no migration_33

