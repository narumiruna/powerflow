//! SMC connection and key reading

use super::ffi::*;
use crate::{PowerError, PowerResult};
use io_kit_sys::types::*;
use io_kit_sys::*;
use mach2::kern_return::*;
use mach2::port::mach_port_t;
use mach2::traps::mach_task_self;

/// SMC connection handle
pub struct SMCConnection {
    connection: io_connect_t,
    service: io_object_t,
}

impl SMCConnection {
    /// Open connection to AppleSMC
    pub fn new() -> PowerResult<Self> {
        unsafe {
            // Get master port
            let mut master_port: mach_port_t = 0;
            let kr = IOMasterPort(0, &mut master_port);
            if kr != KERN_SUCCESS {
                return Err(PowerError::IOKitError(format!(
                    "IOMasterPort failed: {}",
                    kr
                )));
            }

            // Find AppleSMC service
            let matching = IOServiceMatching(b"AppleSMC\0".as_ptr() as *const i8);
            if matching.is_null() {
                return Err(PowerError::IOKitError(
                    "IOServiceMatching failed".to_string(),
                ));
            }

            let mut iterator: io_iterator_t = 0;
            let kr = IOServiceGetMatchingServices(master_port, matching, &mut iterator);
            if kr != KERN_SUCCESS {
                return Err(PowerError::IOKitError(format!(
                    "IOServiceGetMatchingServices failed: {}",
                    kr
                )));
            }

            // Get first matching service
            let service = IOIteratorNext(iterator);
            IOObjectRelease(iterator);

            if service == 0 {
                return Err(PowerError::IOKitError("AppleSMC not found".to_string()));
            }

            // Open connection
            let mut connection: io_connect_t = 0;
            let kr = IOServiceOpen(service, mach_task_self(), 0, &mut connection);
            if kr != KERN_SUCCESS {
                IOObjectRelease(service);
                return Err(PowerError::IOKitError(format!(
                    "IOServiceOpen failed: {}",
                    kr
                )));
            }

            Ok(Self {
                connection,
                service,
            })
        }
    }

    /// Read SMC key and return value as f32
    pub fn read_key(&mut self, key: &str) -> PowerResult<f32> {
        let key_code = str_to_key(key);

        // First get key info (data type and size)
        let key_info = self.read_key_info(key_code)?;

        // Then read the actual value
        let bytes = self.read_key_bytes(key_code, &key_info)?;

        // Convert bytes to f32 based on data type
        let data_type = type_to_str(key_info.data_type);
        let value = Self::bytes_to_float(&bytes, &data_type, key_info.data_size)?;

        Ok(value)
    }

    /// Read key metadata
    fn read_key_info(&mut self, key: u32) -> PowerResult<KeyInfo> {
        unsafe {
            let mut input = SMCKeyData::default();
            let mut output = SMCKeyData::default();

            input.key = key;
            input.data8 = SMC_CMD_READ_KEYINFO;

            let input_size = std::mem::size_of::<SMCKeyData>();
            let mut output_size = std::mem::size_of::<SMCKeyData>();

            let kr = IOConnectCallStructMethod(
                self.connection,
                KERNEL_INDEX_SMC,
                &input as *const _ as *const std::ffi::c_void,
                input_size,
                &mut output as *mut _ as *mut std::ffi::c_void,
                &mut output_size,
            );

            if kr != KERN_SUCCESS {
                return Err(PowerError::IOKitError(format!(
                    "Read key info failed for {}: {}",
                    key_to_str(key),
                    kr
                )));
            }

            Ok(output.key_info)
        }
    }

    /// Read key value bytes
    fn read_key_bytes(&mut self, key: u32, key_info: &KeyInfo) -> PowerResult<Vec<u8>> {
        unsafe {
            let mut input = SMCKeyData::default();
            let mut output = SMCKeyData::default();

            input.key = key;
            input.data8 = SMC_CMD_READ_BYTES;
            input.key_info = *key_info;

            let input_size = std::mem::size_of::<SMCKeyData>();
            let mut output_size = std::mem::size_of::<SMCKeyData>();

            let kr = IOConnectCallStructMethod(
                self.connection,
                KERNEL_INDEX_SMC,
                &input as *const _ as *const std::ffi::c_void,
                input_size,
                &mut output as *mut _ as *mut std::ffi::c_void,
                &mut output_size,
            );

            if kr != KERN_SUCCESS {
                return Err(PowerError::IOKitError(format!(
                    "Read key bytes failed for {}: {}",
                    key_to_str(key),
                    kr
                )));
            }

            // Extract bytes up to data_size
            let size = key_info.data_size as usize;
            Ok(output.bytes[..size].to_vec())
        }
    }

    /// Convert raw bytes to float based on SMC data type
    fn bytes_to_float(bytes: &[u8], data_type: &str, data_size: u32) -> PowerResult<f32> {
        match data_type {
            // Fixed-point types
            "sp78" | "sp87" | "sp96" | "spa5" | "spb4" | "spf0" => {
                // Signed fixed-point, divide by 256
                if bytes.len() < 2 {
                    return Ok(0.0);
                }
                let raw = i16::from_be_bytes([bytes[0], bytes[1]]);
                Ok(raw as f32 / 256.0)
            }
            "fp88" | "fp79" | "fp6a" | "fp4c" => {
                // Unsigned fixed-point, divide by 256
                if bytes.len() < 2 {
                    return Ok(0.0);
                }
                let raw = u16::from_be_bytes([bytes[0], bytes[1]]);
                Ok(raw as f32 / 256.0)
            }
            "flt " => {
                // IEEE 754 float (4 bytes)
                if bytes.len() < 4 {
                    return Ok(0.0);
                }
                let bits = u32::from_be_bytes([bytes[0], bytes[1], bytes[2], bytes[3]]);
                Ok(f32::from_bits(bits))
            }
            "ui8 " => {
                // Unsigned 8-bit integer
                if bytes.is_empty() {
                    return Ok(0.0);
                }
                Ok(bytes[0] as f32)
            }
            "ui16" => {
                // Unsigned 16-bit integer
                if bytes.len() < 2 {
                    return Ok(0.0);
                }
                let val = u16::from_be_bytes([bytes[0], bytes[1]]);
                Ok(val as f32)
            }
            "ui32" => {
                // Unsigned 32-bit integer
                if bytes.len() < 4 {
                    return Ok(0.0);
                }
                let val = u32::from_be_bytes([bytes[0], bytes[1], bytes[2], bytes[3]]);
                Ok(val as f32)
            }
            _ => {
                // Unknown type, try to parse as unsigned integer
                match data_size {
                    1 => Ok(bytes.first().copied().unwrap_or(0) as f32),
                    2 if bytes.len() >= 2 => {
                        Ok(u16::from_be_bytes([bytes[0], bytes[1]]) as f32)
                    }
                    4 if bytes.len() >= 4 => {
                        Ok(u32::from_be_bytes([bytes[0], bytes[1], bytes[2], bytes[3]]) as f32)
                    }
                    _ => Ok(0.0),
                }
            }
        }
    }
}

impl Drop for SMCConnection {
    fn drop(&mut self) {
        unsafe {
            if self.connection != 0 {
                IOServiceClose(self.connection);
            }
            if self.service != 0 {
                IOObjectRelease(self.service);
            }
        }
    }
}
