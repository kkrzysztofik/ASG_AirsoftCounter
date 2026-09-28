//! Admin menu shown after an admin card tap. Red button = next item, blue = select.

use core::fmt::Write;
use heapless::String;

use crate::game::Team;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Item {
    Reset,
    WifiSetup,
    Status,
    Exit,
}

const ITEMS: [(Item, &str); 4] = [
    (Item::Reset, "Reset gry"),
    (Item::WifiSetup, "Ustawienia WiFi"),
    (Item::Status, "Status"),
    (Item::Exit, "Wyjscie"),
];

#[derive(Default)]
pub struct Menu {
    sel: usize,
}

impl Menu {
    pub fn new() -> Self {
        Self { sel: 0 }
    }

    /// Red moves to the next item; blue returns the selected one.
    pub fn press(&mut self, team: Team) -> Option<Item> {
        match team {
            Team::Red => {
                self.sel = (self.sel + 1) % ITEMS.len();
                None
            }
            Team::Blue => Some(ITEMS[self.sel].0),
        }
    }

    /// The four 20-character LCD lines: title, then previous / >current / next item.
    pub fn lines(&self) -> [String<20>; 4] {
        let mut l: [String<20>; 4] = Default::default();
        let _ = write!(l[0], "ADMIN  R>dalej B>ok");
        let n = ITEMS.len();
        for (i, (mark, off)) in [(' ', n - 1), ('>', 0), (' ', 1)].into_iter().enumerate() {
            let _ = write!(l[i + 1], "{mark}{}", ITEMS[(self.sel + off) % n].1);
        }
        l
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn starts_on_reset() {
        assert_eq!(Menu::new().press(Team::Blue), Some(Item::Reset));
    }

    #[test]
    fn red_cycles_through_items_and_wraps() {
        let mut m = Menu::new();
        for want in [Item::WifiSetup, Item::Status, Item::Exit, Item::Reset] {
            assert_eq!(m.press(Team::Red), None);
            assert_eq!(m.press(Team::Blue), Some(want));
        }
    }

    #[test]
    fn blue_returns_selected_item_without_moving() {
        let mut m = Menu::new();
        m.press(Team::Red);
        assert_eq!(m.press(Team::Blue), Some(Item::WifiSetup));
        assert_eq!(m.press(Team::Blue), Some(Item::WifiSetup));
        assert_eq!(m.lines()[2].as_str(), ">Ustawienia WiFi");
    }

    #[test]
    fn initial_lines() {
        let l = Menu::new().lines();
        assert_eq!(
            l.each_ref().map(|s| s.as_str()),
            ["ADMIN  R>dalej B>ok", " Wyjscie", ">Reset gry", " Ustawienia WiFi"]
        );
    }

    #[test]
    fn lines_fit_the_20x4_lcd() {
        let mut m = Menu::new();
        for (_, label) in ITEMS {
            let l = m.lines();
            // String<20> can't overflow, but a label that doesn't fit would be silently dropped.
            assert_eq!(&l[2][1..], label);
            assert!(l.iter().all(|s| s.len() <= 20));
            m.press(Team::Red);
        }
    }
}
