//! Low-level FFI bindings for SMC access via IOKit

#![allow(non_upper_case_globals)]
#![allow(non_camel_case_types)]
#![allow(non_snake_case)]
#![allow(dead_code)]

// SMC key codes
pub const KERNEL_INDEX_SMC: u32 = 2;
pub const SMC_CMD_READ_BYTES: u8 = 5;
pub const SMC_CMD_READ_KEYINFO: u8 = 9;

// Data structure sizes
pub const SMC_KEY_SIZE: usize = 4;
pub const SMC_DATA_SIZE: usize = 32;
pub const SMC_BYTES_SIZE: usize = 32;

/// SMC key data structure (80 bytes)
#[repr(C, packed)]
pub struct SMCKeyData {
    pub key: u32,
    pub vers: SMCVersion,
    pub p_limit_data: SMCPLimitData,
    pub key_info: KeyInfo,
    pub result: u8,
    pub status: u8,
    pub data8: u8,
    pub data32: u32,
    pub bytes: [u8; SMC_BYTES_SIZE],
}

impl Default for SMCKeyData {
    fn default() -> Self {
        unsafe { std::mem::zeroed() }
    }
}

#[repr(C, packed)]
pub struct SMCVersion {
    pub major: u8,
    pub minor: u8,
    pub build: u8,
    pub reserved: u8,
    pub release: u16,
}

impl Default for SMCVersion {
    fn default() -> Self {
        unsafe { std::mem::zeroed() }
    }
}

#[repr(C, packed)]
pub struct SMCPLimitData {
    pub version: u16,
    pub length: u16,
    pub cpu_plimit: u32,
    pub gpu_plimit: u32,
    pub mem_plimit: u32,
}

impl Default for SMCPLimitData {
    fn default() -> Self {
        unsafe { std::mem::zeroed() }
    }
}

#[repr(C, packed)]
#[derive(Debug, Clone, Copy)]
pub struct KeyInfo {
    pub data_size: u32,
    pub data_type: u32,
    pub data_attributes: u8,
}

impl Default for KeyInfo {
    fn default() -> Self {
        unsafe { std::mem::zeroed() }
    }
}

/// Convert 4-character key to u32 (big-endian)
pub fn str_to_key(s: &str) -> u32 {
    let bytes = s.as_bytes();
    if bytes.len() != 4 {
        return 0;
    }
    u32::from_be_bytes([bytes[0], bytes[1], bytes[2], bytes[3]])
}

/// Convert u32 key to 4-character string
pub fn key_to_str(key: u32) -> String {
    let bytes = key.to_be_bytes();
    String::from_utf8_lossy(&bytes).to_string()
}

/// Convert data type u32 to string
pub fn type_to_str(data_type: u32) -> String {
    let bytes = data_type.to_be_bytes();
    String::from_utf8_lossy(&bytes).to_string()
}
