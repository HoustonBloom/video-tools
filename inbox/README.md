# inbox

Put a video file here, with its caption file if the platform gave you one.
The tools write their output into a folder beside it named after the video,
so one recording's captions, frames and page stay together and two
recordings never write over each other.

```
inbox/
  my-recording.mp4
  my-recording/
    my-recording.vtt        made by transcribe if you had none
    readthrough.html        made by readthrough
    stills/                 made by stills
    renders/                a cut, a tightened take, a loudness fix: the plan and the file
```

Media never enters the repository; `.gitignore` refuses it by extension. The
folder is here so there is one obvious place to drop a file.
