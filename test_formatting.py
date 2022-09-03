from miniirc_discord import _irc_to_discord

def test_irc_to_discord():
    assert _irc_to_discord('Hello \x02world\x02!') == 'Hello **world**!'
    assert _irc_to_discord('Hello\x02 world\x02!') == 'Hello** world**!'
    assert _irc_to_discord('*Test*\x1d message') == '\\*Test\\*_ message_'
    assert _irc_to_discord('Test\x11 message') == 'Test` message`'

    # Keep the (broken) 0.5.x behaviour for now
    assert _irc_to_discord('Test with `code`') == 'Test with `code`'
    assert _irc_to_discord(r'Test with \`code\`') == r'Test with \\`code\\`'

    # Spoilers
    assert _irc_to_discord('Hello \x031,1world\x03!') == 'Hello ||world||!'
    assert _irc_to_discord('Hello \x031,2world\x03!') == 'Hello world!'
    assert _irc_to_discord('Hello \x031,01world\x031!') == 'Hello ||world||!'
    assert _irc_to_discord('Hello \x03,1world\x031!') == 'Hello world!'
    assert _irc_to_discord('Hello \x031world\x03,2!') == 'Hello world!'
