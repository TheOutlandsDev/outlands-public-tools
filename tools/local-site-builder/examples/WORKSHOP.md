# First site: a fictional workshop guide

This walkthrough uses original, fictional content. No purchase, medical claim,
real business identity or external service account is needed. Define
`$privateWork` outside the entire checkout using the
[private workspace guide](https://github.com/TheOutlandsDev/outlands-public-tools/blob/main/docs/PRIVATE-WORKSPACE.md) before the setup commands.

1. Follow the README setup. Open `/admin` and sign in with your local account.
2. On Welcome, change the Headline to **Build something useful** and Body to
   **Small projects, clear instructions, and room to improve.** Click Save Draft.
3. Open `/` separately. It should still show the earlier published page. Click
   Publish in the editor, then refresh `/`; your edited headline should appear.
4. Click the Guide page template. Enter **Making a simple shelf** when prompted.
   Its generated slug should be `making-a-simple-shelf`. Edit the checklist:
   **Plan the size**, **Gather materials**, **Review the result**.
5. Save Draft. The public URL should return Page not found while this new page
   is unpublished. Publish, add it to Site Menu and save that menu.
6. Upload an image you own, add an Image + Text block, select the asset, and click
   Insert. Use a fictional description. Save and publish. Original image metadata
   is retained; do not use a private photo just to test the editor.
7. Optionally create a Community page. Submit a clearly fictional message such
   as `Demo Visitor`, `demo@example.invalid`, `This is a local test.` Check Inbox.
   With default settings, the message stays local and no email is sent.
8. Stop with Ctrl+C. Create and verify `"$privateWork/workshop-backup-001"` using the README
   commands. Restore to `"$privateWork/workshop-restored-data"`, select that root and restart.
   Check that published pages, drafts, images and the demo message are present.
9. Stop again and export to `"$privateWork/workshop-static-001"`. Inspect its files before any
   deployment. It should contain published pages/assets and no database, admin
   interface, private draft, inbox or `.env`. Contact forms are replaced with a
   static explanation because there is no backend at an ordinary static host.

For an automated version, `npm test` creates its own small sites, image bytes and
backups, verifies results, and removes only its owned temporary fixture directory.
It never imports or resets your existing website.
