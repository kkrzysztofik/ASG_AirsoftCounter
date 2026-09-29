#![no_std]

#[cfg(not(any(all(feature = "v4-r2", not(feature = "v4-r8")), all(feature = "v4-r8", not(feature = "v4-r2")))))]
compile_error!("enable exactly one board variant feature: `v4-r2` or `v4-r8`");

pub mod board;
