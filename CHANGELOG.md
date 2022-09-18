# Changelog

Format partially copied from [Keep a Changelog](https://keepachangelog.com).

## 0.6.1 - 2022-09-18

### Changed

 - Markdown should now be escaped better when using code blocks.

## 0.6.0 - 2022-09-03

### Added

 - Support for replies and reactions using the `+draft/reply` and `+draft/react` message tags.
 - Better formatting support, for example spoilers and strikethrough are now
   correctly relayed to Discord.
 - Embeds can now have their title set to the first line of the NOTICE rather
   than a non-standard message tag.
 - Support for 2-digit colour codes in embeds.
 - The `bot` message tag is added to messages sent by bots.

### Changed

 - Updated to discord.py v2.
 - The `stateless_mode` keyword argument now defaults to True.
 - When `stateless_mode` is enabled, miniirc_discord will now only request the
   `messages`, `message_content`, and `reactions` intents.
 - Markdown spoilers and strikethrough (`||` and `~~`) are now escaped and
   won't work.

## 0.5.18 - 2020-06-27

### Added

 - A `discord_client` attribute.
 - A `stateless_mode` keyword argument that removes the above attribute and disables discord.py's user cache to save RAM.
