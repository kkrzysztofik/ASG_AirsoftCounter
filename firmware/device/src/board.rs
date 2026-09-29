//! Heltec WiFi LoRa 32 V4 (no display) + AirsoftCounter carrier. See design doc parts 1 and 6.
//! The only file that names GPIOs: the numbers below document the map, `Board::new` hands out the
//! matching typed pins by role.

use esp_hal::gpio::AnyPin;
use esp_hal::peripherals::{FROM_CPU_INTR0, Peripherals, TIMG0};

pub const I2C_SDA: u8 = 4;
pub const I2C_SCL: u8 = 3;
pub const EXP_INT: u8 = 6; // TCA9534 INT, active low, 10k pull-up on the carrier
pub const I2S_BCLK: u8 = 47;
pub const I2S_LRCLK: u8 = 48;
pub const I2S_DIN: u8 = 21;
pub const VBAT_ADC: u8 = 1;
// GPIO44 (U0RXD) and GPIO43 (U0TXD) are spare and unconnected; never enable UART0.

/// TCA9534 expander (I2C 0x20) pin map.
pub mod exp {
    pub const ADDR: u8 = 0x20;
    pub const BTN_RED: u8 = 0; // input, active low
    pub const BTN_BLUE: u8 = 1; // input, active low
    pub const LED_RED: u8 = 2;
    pub const LED_BLUE: u8 = 3;
    pub const BUZZER: u8 = 4;
    pub const AMP_SD: u8 = 5; // high = amp on (left channel), low = shutdown
    // P6, P7 unconnected: configure as outputs driven low.
}
#[cfg(feature = "v4-r2")]
pub const ONBOARD_LED: u8 = 35;
#[cfg(feature = "v4-r8")]
pub const ONBOARD_LED: u8 = 46;
#[cfg(feature = "v4-r2")]
pub const VEXT: u8 = 36; // active low
#[cfg(feature = "v4-r8")]
pub const VEXT: u8 = 40;
#[cfg(feature = "v4-r2")]
pub const ADC_CTRL: Option<u8> = Some(37);
#[cfg(feature = "v4-r8")]
pub const ADC_CTRL: Option<u8> = None;

/// Peripherals split by role. Later tasks add fields here (I2C, I2S, ADC, ...).
pub struct Board {
    pub onboard_led: AnyPin<'static>,
    /// For the esp-rtos scheduler.
    pub timg0: TIMG0<'static>,
    pub sw_int0: FROM_CPU_INTR0<'static>,
}

impl Board {
    pub fn new(p: Peripherals) -> Self {
        #[cfg(feature = "v4-r2")]
        let onboard_led = p.GPIO35.into();
        #[cfg(feature = "v4-r8")]
        let onboard_led = p.GPIO46.into();
        Self { onboard_led, timg0: p.TIMG0, sw_int0: p.FROM_CPU_INTR0 }
    }
}
