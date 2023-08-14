############
## GENERAL
############

## Token for the discord bot
DISCORD_TOKEN = ""

## Directory to save the caller's avatar and name
CALLER_DATA_DIR = "path/to/dir"

## How long the invite is valid for in seconds
INVITE_DURATION_SECONDS = 3 * 3600

############
## CAPTCHA SETTINGS
############

## Whether or not to ask the user a captcha to solve
USE_CAPTCHA = True

## How long to wait before booting the caller for inactivity
CAPTCHA_TIMEOUT_SECONDS = 2*60

############
## QUEUE MANAGEMENT
############

## Maximum queue size. Must be at most the number of slots available
## Can be used to to artificially limit the cue without deleting rooms
QUEUE_LIMIT = 15

## A symbol to prefix to the caller's name
## Makes it easier to see who has been verified
VERIFICATION_SYMBOL = "✅"

## The message shown to the user when they've been given a room in the server
## Can include rules and an introduction
## Make use of "<@{user_id}>" to mention the caller
## and "<#{voice_channel_id}>" to mention the voice channel
ASSIGNED_ROLE_MESSAGE = """Hello <@{user_id}>!

When you're ready, join the <#{voice_channel_id}> channel."""

## DM sent to the user when all rooms are full.
## Ask the user to wait for space to free up and they will automatically be given a room
FULL_QUEUE_MESSAGE = """Message"""

## DM sent to all users when they've been booted after using the "Clear All" command
END_STREAM_MESSAGE = """Message"""
