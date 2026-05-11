# 🤖 AI AGENT OPERATIONAL RULES (MANDATORY)

To ensure the integrity and safety of the MoneyFlow trading system, ALL AI agents must follow these strict protocols:

## 1. Mandatory Git Synchronization
*   **Action:** Every single code modification must be followed by a `git push`.
*   **Why:** To ensure the local machine, the production server, and the cloud backup (GitHub) are always identical. This prevents "lost" fixes during server migrations.

## 2. Mandatory Documentation Updates
*   **Action:** Any change to the bot's behavior, timing, or logic must be updated in the **Walkthrough** and **Rulebook/README**.
*   **Why:** To ensure the user always has a clear, stepwise understanding of how the current version of the bot executes.

## 3. Infrastructure Integrity
*   **Action:** If a server is changed or launched, the **AWS Lambda Trigger (Alarm)** must be updated to point to the new Instance ID.
*   **Why:** To ensure the daily 9:15 AM and 3:00 PM automation never fails.

## 4. Mandatory Server Shutdown
*   **Action:** Before signing off, always verify that the EC2 instance is in a **Stopped** state (unless explicitly asked otherwise).
*   **Why:** To prevent unnecessary AWS costs and ensure a fresh startup for the next scheduled run.

---
*Follow these rules to ensure a professional, production-grade environment.*
