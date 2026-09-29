//! Airsoftcoin game rules, ported from the Arduino state machine.
//! Pure logic: time comes in as milliseconds, effects go out as return values.

use core::fmt::Write;
use heapless::String;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Team {
    Red,
    Blue,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Config {
    pub mining_time_s: u16,
    pub block_size: u16,
}

impl Default for Config {
    fn default() -> Self {
        Self { mining_time_s: 5, block_size: 3 }
    }
}

impl Config {
    /// Limits from the original IR config menu.
    pub fn clamped(self) -> Self {
        Self { mining_time_s: self.mining_time_s.clamp(5, 30000), block_size: self.block_size.clamp(1, 1000) }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Leds {
    Blink,
    On,
    Off,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Beep {
    pub on_ms: u16,
    pub off_ms: u16,
    pub times: u8,
}

pub const READY_BEEP: Beep = Beep { on_ms: 200, off_ms: 100, times: 3 };
pub const MINED_BEEP: Beep = Beep { on_ms: 200, off_ms: 200, times: 5 };

const INTRO_MS: u64 = 3000;
const READY_BEEP_EVERY_MS: u64 = 15000;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Phase {
    Intro { until: u64 },
    Ready { next_beep: u64 },
    Mining { left_s: u16, next_tick: u64 },
    Depleted { since: u64 },
}

pub struct Game {
    phase: Phase,
    red: u16,
    blue: u16,
    left: u16,
    cfg: Config,
}

impl Game {
    pub fn new(cfg: Config, now: u64) -> Self {
        let cfg = cfg.clamped();
        Self { phase: Phase::Intro { until: now + INTRO_MS }, red: 0, blue: 0, left: cfg.block_size, cfg }
    }

    pub fn phase(&self) -> Phase {
        self.phase
    }

    /// (red, blue) captures.
    pub fn score(&self) -> (u16, u16) {
        (self.red, self.blue)
    }

    pub fn left(&self) -> u16 {
        self.left
    }

    /// Advance time. Returns a beep pattern to play, if any.
    pub fn tick(&mut self, now: u64) -> Option<Beep> {
        match self.phase {
            Phase::Intro { until } if now >= until => {
                self.phase = Phase::Ready { next_beep: now + READY_BEEP_EVERY_MS };
                None
            }
            Phase::Ready { next_beep } if now >= next_beep => {
                self.phase = Phase::Ready { next_beep: now + READY_BEEP_EVERY_MS };
                Some(READY_BEEP)
            }
            Phase::Mining { mut left_s, mut next_tick } if now >= next_tick => {
                while now >= next_tick && left_s > 0 {
                    left_s -= 1;
                    next_tick += 1000;
                }
                if left_s == 0 {
                    self.phase = Phase::Ready { next_beep: now + READY_BEEP_EVERY_MS };
                    return Some(MINED_BEEP);
                }
                self.phase = Phase::Mining { left_s, next_tick };
                None
            }
            _ => None,
        }
    }

    /// A team captured the coin (button or player card). Returns true if it counted.
    pub fn capture(&mut self, team: Team, now: u64) -> bool {
        if !matches!(self.phase, Phase::Ready { .. }) {
            return false;
        }
        match team {
            Team::Red => self.red += 1,
            Team::Blue => self.blue += 1,
        }
        self.left -= 1;
        self.phase = if self.left == 0 {
            Phase::Depleted { since: now }
        } else {
            Phase::Mining { left_s: self.cfg.mining_time_s, next_tick: now + 1000 }
        };
        true
    }

    pub fn leds(&self) -> Leds {
        match self.phase {
            Phase::Intro { .. } => Leds::Blink,
            Phase::Ready { .. } => Leds::On,
            Phase::Mining { .. } | Phase::Depleted { .. } => Leds::Off,
        }
    }

    /// LCD backlight: blinks once per second when the point is depleted.
    pub fn backlight(&self, now: u64) -> bool {
        match self.phase {
            Phase::Depleted { since } => (now.saturating_sub(since) / 1000).is_multiple_of(2),
            _ => true,
        }
    }

    /// The four 20-character LCD lines.
    pub fn lines(&self) -> [String<20>; 4] {
        let mut l: [String<20>; 4] = Default::default();
        // Lines are <= 20 chars for all counts <= 9999 (counts are bounded by block_size <= 1000).
        let _ = write!(l[0], "{:<16}{:>4}", "Czerwoni", self.red);
        let _ = write!(l[1], "{:<16}{:>4}", "Niebiescy", self.blue);
        let _ = match self.phase {
            Phase::Intro { .. } => write!(l[2], "Tryb Airsoftcoin"),
            Phase::Ready { .. } => write!(l[2], "GOTOWY"),
            Phase::Mining { left_s, .. } => write!(l[2], "Kopanie {:02}:{:02}", left_s / 60, left_s % 60),
            Phase::Depleted { .. } => write!(l[2], "PUNKT WYCZERPANY"),
        };
        let _ = write!(l[3], "{:<16}{:>4}", "Pozostalo", self.left);
        l
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn ready_game(cfg: Config) -> Game {
        let mut g = Game::new(cfg, 0);
        assert_eq!(g.tick(3000), None);
        g
    }

    #[test]
    fn intro_lasts_three_seconds_with_blinking_leds() {
        let mut g = Game::new(Config::default(), 0);
        assert_eq!(g.leds(), Leds::Blink);
        g.tick(2999);
        assert!(matches!(g.phase, Phase::Intro { .. }));
        g.tick(3000);
        assert!(matches!(g.phase, Phase::Ready { .. }));
        assert_eq!(g.leds(), Leds::On);
    }

    #[test]
    fn ready_beeps_every_15_seconds() {
        let mut g = ready_game(Config::default());
        assert_eq!(g.tick(17999), None);
        assert_eq!(g.tick(18000), Some(READY_BEEP));
        assert_eq!(g.tick(18001), None);
        assert_eq!(g.tick(33000), Some(READY_BEEP));
    }

    #[test]
    fn ready_beep_skips_missed_intervals_after_a_stall() {
        let mut g = ready_game(Config::default());
        assert_eq!(g.tick(18_000), Some(READY_BEEP));
        assert_eq!(g.tick(100_000), Some(READY_BEEP));
        assert_eq!(g.tick(100_001), None);
    }

    #[test]
    fn capture_while_depleted_does_not_count() {
        let mut g = ready_game(Config { mining_time_s: 5, block_size: 1 });
        assert!(g.capture(Team::Red, 5000));
        assert!(!g.capture(Team::Blue, 6000));
        assert_eq!((g.red, g.blue, g.left), (1, 0, 0));
    }

    #[test]
    fn lcd_shows_four_digit_counts() {
        let g = ready_game(Config { mining_time_s: 5, block_size: 1000 });
        assert_eq!(g.lines()[3].as_str(), "Pozostalo       1000");
    }

    #[test]
    fn capture_only_counts_when_ready() {
        let mut g = Game::new(Config::default(), 0);
        assert!(!g.capture(Team::Red, 100));
        g.tick(3000);
        assert!(g.capture(Team::Red, 3100));
        assert!(!g.capture(Team::Blue, 3200)); // mining now
        assert_eq!((g.red, g.blue, g.left), (1, 0, 2));
    }

    #[test]
    fn mining_counts_down_then_beeps_and_is_ready_again() {
        let mut g = ready_game(Config { mining_time_s: 5, block_size: 3 });
        g.capture(Team::Blue, 10_000);
        assert_eq!(g.leds(), Leds::Off);
        assert_eq!(g.tick(11_000), None);
        assert!(matches!(g.phase, Phase::Mining { left_s: 4, .. }));
        assert_eq!(g.tick(14_999), None);
        assert_eq!(g.tick(15_000), Some(MINED_BEEP));
        assert!(matches!(g.phase, Phase::Ready { .. }));
    }

    #[test]
    fn late_tick_catches_up() {
        let mut g = ready_game(Config { mining_time_s: 5, block_size: 3 });
        g.capture(Team::Blue, 10_000);
        assert_eq!(g.tick(13_500), None);
        assert!(matches!(g.phase, Phase::Mining { left_s: 2, next_tick: 14_000 }));
    }

    #[test]
    fn last_capture_depletes_the_point_and_blinks_backlight() {
        let mut g = ready_game(Config { mining_time_s: 5, block_size: 1 });
        assert!(g.capture(Team::Red, 5000));
        assert!(matches!(g.phase, Phase::Depleted { .. }));
        assert_eq!(g.tick(60_000), None);
        assert!(g.backlight(5500));
        assert!(!g.backlight(6500));
        assert!(g.backlight(7500));
    }

    #[test]
    fn config_is_clamped() {
        let g = Game::new(Config { mining_time_s: 1, block_size: 0 }, 0);
        assert_eq!(g.left, 1);
        assert_eq!(
            Config { mining_time_s: 60000, block_size: 5000 }.clamped(),
            Config { mining_time_s: 30000, block_size: 1000 }
        );
    }

    #[test]
    fn lines_fit_the_20x4_lcd() {
        let mut g = ready_game(Config { mining_time_s: 30000, block_size: 1000 });
        g.capture(Team::Red, 4000);
        let l = g.lines();
        assert_eq!(l[0].as_str(), "Czerwoni           1");
        assert_eq!(l[2].as_str(), "Kopanie 500:00");
        assert_eq!(l[3].as_str(), "Pozostalo        999");
        assert!(l.iter().all(|s| s.len() <= 20));
    }
}
