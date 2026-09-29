//! Player card format: NTAG21x with one NDEF text record `ASG1:<R|B>:<id>`.
//! Input is the tag memory starting at page 4 (the first user page).

use crate::game::Team;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct PlayerCard {
    pub team: Team,
    pub id: u16,
}

pub fn parse_player_card(mem: &[u8]) -> Option<PlayerCard> {
    parse_text(ndef_message(mem)?).and_then(|t| core::str::from_utf8(t).ok()).and_then(parse_asg)
}

/// Walk the TLV blocks and return the NDEF message body.
fn ndef_message(mem: &[u8]) -> Option<&[u8]> {
    let mut i = 0;
    while i < mem.len() {
        match mem[i] {
            0x00 => i += 1,      // NULL TLV
            0xFE => return None, // terminator before any NDEF TLV
            tag => {
                let (len, hdr) = match *mem.get(i + 1)? {
                    0xFF => (u16::from_be_bytes([*mem.get(i + 2)?, *mem.get(i + 3)?]) as usize, 4),
                    l => (l as usize, 2),
                };
                let body = mem.get(i + hdr..i + hdr + len)?;
                if tag == 0x03 {
                    return Some(body);
                }
                i += hdr + len; // lock / memory control / proprietary TLVs
            }
        }
    }
    None
}

/// First record must be a short well-known "T" (text) record.
fn parse_text(msg: &[u8]) -> Option<&[u8]> {
    let [header, type_len, payload_len, rest @ ..] = msg else { return None };
    let short = header & 0x10 != 0;
    let well_known = header & 0x07 == 0x01;
    let has_id = header & 0x08 != 0;
    if !short || !well_known || has_id || *type_len != 1 || rest.first() != Some(&b'T') {
        return None;
    }
    let payload = rest.get(1..1 + *payload_len as usize)?;
    let lang_len = (*payload.first()? & 0x3F) as usize;
    payload.get(1 + lang_len..)
}

fn parse_asg(text: &str) -> Option<PlayerCard> {
    let mut parts = text.trim().split(':');
    if parts.next()? != "ASG1" {
        return None;
    }
    let team = match parts.next()? {
        "R" => Team::Red,
        "B" => Team::Blue,
        _ => return None,
    };
    let id: u16 = parts.next()?.parse().ok()?;
    if parts.next().is_some() || !(1..=999).contains(&id) {
        return None;
    }
    Some(PlayerCard { team, id })
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Tag memory as a phone NFC app writes it: NDEF TLV, text record, terminator.
    fn tag(text: &str) -> heapless::Vec<u8, 64> {
        let mut v = heapless::Vec::new();
        let payload_len = 3 + text.len() as u8; // status byte + "en" + text
        v.extend_from_slice(&[0x03, 4 + payload_len, 0xD1, 0x01, payload_len, b'T', 0x02, b'e', b'n']).unwrap();
        v.extend_from_slice(text.as_bytes()).unwrap();
        v.push(0xFE).unwrap();
        v
    }

    #[test]
    fn parses_red_and_blue_cards() {
        assert_eq!(parse_player_card(&tag("ASG1:R:017")), Some(PlayerCard { team: Team::Red, id: 17 }));
        assert_eq!(parse_player_card(&tag("ASG1:B:999")), Some(PlayerCard { team: Team::Blue, id: 999 }));
    }

    #[test]
    fn skips_lock_control_tlv() {
        let mut mem: heapless::Vec<u8, 64> = heapless::Vec::new();
        mem.extend_from_slice(&[0x01, 0x03, 0xA0, 0x10, 0x44]).unwrap();
        mem.extend_from_slice(&tag("ASG1:B:5")).unwrap();
        assert_eq!(parse_player_card(&mem), Some(PlayerCard { team: Team::Blue, id: 5 }));
    }

    #[test]
    fn parses_three_byte_tlv_length() {
        let t = tag("ASG1:R:42");
        let mut mem: heapless::Vec<u8, 64> = heapless::Vec::new();
        mem.extend_from_slice(&[0x03, 0xFF, 0x00, t[1]]).unwrap();
        mem.extend_from_slice(&t[2..]).unwrap();
        assert_eq!(parse_player_card(&mem), Some(PlayerCard { team: Team::Red, id: 42 }));
    }

    #[test]
    fn rejects_uri_record() {
        let mut mem = tag("ASG1:R:1");
        mem[5] = b'U';
        assert_eq!(parse_player_card(&mem), None);
    }

    #[test]
    fn rejects_bad_content() {
        for t in ["ASG1:G:1", "ASG1:R:0", "ASG1:R:1000", "ASG2:R:1", "ASG1:R:1:x", "hello"] {
            assert_eq!(parse_player_card(&tag(t)), None, "{t}");
        }
        assert_eq!(parse_player_card(&[0xFE]), None);
        assert_eq!(parse_player_card(&[0x03, 0x20, 0xD1]), None); // truncated
        assert_eq!(parse_player_card(&[]), None);
    }
}
