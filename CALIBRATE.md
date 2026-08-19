# Calibration

## Volunteers

```bash
git clone https://github.com/dgutson/check-chat.git ~/check-chat
~/check-chat/bin/checkchat --calibrate
```

Needs `python3` (3.9 or newer) and nothing else — no install, no virtualenv, no network, and
nothing is sent anywhere. It reads the Claude Code transcripts already on your machine and
takes about twenty seconds.

It writes `~/checkchat-calibration.txt`. **Read that file before you send it.** Its first
lines say exactly what it carries, and it is *not* anonymous: rows quote file paths, commands
and the opening of your own prompts, each with a date, a project directory name and a session
id. No assistant replies and no file contents.

Marking it is optional and the fast path is to mark nothing. A blank row counts as *the tool
was right*, so put `b` only in the box of a row it got **wrong**, `?` in one you cannot tell
about — and tick the `read_all` box at the top if you read every row, since blanks only count
for anything when you have.

Then send me `~/checkchat-calibration.txt`.

If it reports `FROM 0 session transcripts`, it looked in `~/.claude/projects` and found
nothing — that is a machine or a user account that has not run Claude Code, and the file it
wrote is empty of findings.

## Daniel

```bash
git push                                                    # volunteers clone this
~/src/check-chat/bin/checkchat --calibrate-merge <their files>
```

The path is not decoration: `checkchat` is on `PATH` **only inside Claude Code**, which adds
this repository's `bin/` for you, so a plain terminal cannot find it by name. The merge reads
each file's build from its data block, prints it per file, and warns when a stack spans
builds — rows from two builds are counts of two populations and pool into a rate describing
neither.
