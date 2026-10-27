---
name: human-communication-consent
description: >
  Carl's rule that every message to other people goes through his explicit OK first.
  Read BEFORE opening a pull request or issue, posting a comment or review, requesting
  reviewers, assigning someone, @-mentioning anyone, sending email or chat messages, or
  sharing a link with anyone. Draft the text and wait for his OK, or hand it to him to send.
---

# Messages to other people need Carl's OK first

Anything that other people will see or be notified about goes through Carl first. Either he
says OK to the exact text before it is sent, or he sends it himself. Permission to do the
technical work is not permission to communicate about it.

## What counts

- Opening a pull request or an issue, including a draft PR, and editing the title or body of
  one that other people can see.
- Comments, reviews, review requests, approvals, assignments, labels that notify people, and
  closing or reopening someone else's PR or issue.
- Any @-mention, in any text, anywhere.
- Email, Slack, chat, calendar invitations, and sharing a document or artifact with someone.
- Automation that does any of these, such as a workflow that comments on PRs. Prefer a check
  status or job summary over a bot comment, and ask before adding a bot that posts.

These do not need a separate OK when they are part of the task he asked for: local commits,
and pushing a feature branch to a remote (not `main` or another deploy branch).

## How to do it

1. Do the technical work: commits, a pushed branch, a built preview.
2. Show Carl the exact text you would post (title, body, where it goes) and stop. Ask him
   whether to send it, or give him the `gh` command so he can run it himself with `! `.
3. Send it only after he says OK to that text, and only once. An OK covers that message only,
   not later ones.

## Names and handles

- Never guess anyone's GitHub handle, email or chat name, and never @-mention someone to get
  their attention. Refer to people by role ("the web developer") unless Carl gives the handle
  and asks for the mention.

## If something was sent by mistake

Tell Carl straight away what was sent, where, and to whom, and whether anyone was notified.
Editing or deleting a post does not take back a notification that has already gone out.
