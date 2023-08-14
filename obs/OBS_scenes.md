# Scenes
| Scene        | Description                                                   |
| ------------ | ------------------------------------------------------------- |
| Final        | The scene that you will always be on. Never change from this. |
| ----         | Separator                                                     |
| Delayed-Main | Contains a delayed version of "Live-Main"                     |
| Live-Main    | Contains all the subscenes and transitions                    |
| Live-Solo    | The screen when you are not in a call                         |
| Live-Call    | The screen for calls                                          |

## Final
- CoverGroup (Group)
  - (Whichever elements you like. Must cover the entire screen)
- Delayed-Main (Scene)
  - Filter: 14x Render Delay (500ms)

## Delayed-Main
- Live-Main (Scene)

## Live-Main
- Live-CallGroup (Group)
  - [For the group, right click > Show Transition and Hide Transition]
  - Live-Call (Scene)
- Live-Solo (Scene)
  - (Right click > Show Transition and Hide Transition)

## Live-Solo
- MainGroup (Group)
  - Microphone
    - Filter: Noise Suppression
  - Discord Audio
  - Webcam
- BG

## Live-Call
- CallGroup (Group)
  - ProfilePicture (Image)
    - Image File: "/path/to/caller_pfp.png"
    - Enable "Unload image when not showing"
    - Filter: Image Mask/Blend
      - Type: Alpha Mask (Alpha Channel)
      - Path: /path/to/obs/pfp_mask.png
      - Enable "Stretch Image"
  - CallerName (Text)
    - Enable "Read from file"
    - Text File: "/path/to/caller_name.txt"
    - Alignment: Center
    - Vertical Alignment: Center
    - Width: 640
    - Height: 100
  - Waveform (Waveform)
    - Audio Source: "Discord Audio"
    - Display Mode: Bars
    - Bar Width: 20
    - Minimum Bar Height: 2
    - Enable "Logarithmic Frequency Scale"
    - Channel Mode: Stereo
    - Channel Spacing: 6
    - Gravity: 0.3
    - Low Cutoff: 20
    - High Cutoff: 4000
  - BG (Color or Image)
- MainGroup (Group)
  - (Copy it from `Live-Solo` then Paste (Reference))