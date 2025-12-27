use thiserror::Error;

/// Result type for power operations
pub type PowerResult<T> = Result<T, PowerError>;

/// Errors that can occur during power monitoring
#[derive(Error, Debug)]
pub enum PowerError {
    #[error("Failed to execute command: {0}")]
    CommandFailed(String),

    #[error("Failed to parse ioreg output: {0}")]
    ParseError(String),

    #[error("Missing required field: {0}")]
    MissingField(&'static str),

    #[error("Platform not supported (macOS required)")]
    UnsupportedPlatform,

    #[error("IOKit error: {0}")]
    IOKitError(String),

    #[error(transparent)]
    Io(#[from] std::io::Error),

    #[error(transparent)]
    Plist(#[from] plist::Error),
}
