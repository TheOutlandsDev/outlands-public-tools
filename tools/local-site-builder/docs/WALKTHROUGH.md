# Draft, publish and recover

[Watch the 60-second captioned walkthrough](https://connor-oshea-outlands.thatrobotguy.chatgpt.site/#local-site-builder-walkthrough)
· [Portfolio case study](https://connor-oshea-outlands.thatrobotguy.chatgpt.site/#local-site-builder)

The walkthrough is assembled from actual Chromium screenshots of the running
Node/SQLite application. It uses the original fictional Cedar Workshop starter,
edited step timing and captions, with no audio. It is not a continuous screen
recording. Browser automation performs the intervening CLI/recovery operations;
the video captions describe those checks, rather than showing a terminal.

| Time | What is demonstrated |
| --- | --- |
| 00:00 | The separate public page starts with “Welcome”. |
| 00:12 | Save “Weekend repair guide” as a private draft; reload it in the editor while the public page stays unchanged. |
| 00:24 | Select Publish; the separate public browser now displays “Weekend repair guide”. |
| 00:36 | Save a newer draft, stop cleanly, create/verify the backup, and restore into a new directory. Tampering and an existing destination are refused. |
| 00:48 | Reopen the restored data: the editor retains “Next workshop guide — draft only”; the public page retains the earlier published headline. |

Actual source captures:

- [Private draft in the editor](screenshots/private-draft.jpg)
- [Published public page](screenshots/published-page.jpg)
- [Restored private draft](screenshots/restored-draft.jpg)

[verification-browser.json](verification-browser.json) records the runtime,
completed acceptance phases, capture hashes and runtime source hashes. The
screenshots are frozen evidence from that run. Later CI runs keep their own
synthetic captures as time-limited artifacts and do not regenerate these files.
No real user content, account, images, inbox, credentials or original private
site was used. The known password was generated only for the disposable fixture.

See [test reproduction and CI scope](BROWSER-CHECKS.md). Backups contain private
state and stay outside the public release; a capture does not itself prove
backup integrity. The test verifies hashes and reopens the restored application.
