def sync_reports_to_git():
    """Commit and push updated reports to GitHub before shutdown."""
    logger.info("Syncing reports to GitHub...")
    try:
        # Add only the reports folder
        subprocess.run(["git", "add", "project/reports/*.csv"], check=True)
        
        # Commit with today's date
        date_str = datetime.now().strftime("%Y-%m-%d")
        msg = f"Auto-update reports: {date_str}"
        subprocess.run(["git", "commit", "-m", msg], check=True)
        
        # Push to remote
        subprocess.run(["git", "push"], check=True)
        logger.info("Reports synced successfully!")
    except Exception as e:
        logger.warning(f"Git sync skipped or failed: {e}")

def shutdown_ec2(dry_run=False):
    """Shutdown the EC2 instance after execution."""
    if dry_run:
        logger.info("[DRY RUN] Would sync and shutdown EC2 now.")
        return
    
    # Sync reports to GitHub so they are available locally
    sync_reports_to_git()
    
    logger.info("Shutting down EC2 instance...")
    notifications.send_shutdown_msg()

    try:
        subprocess.run(["sudo", "shutdown", "-h", "now"], check=False)
    except Exception as e:
        logger.error(f"Shutdown command failed: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Live Trading Bot")
    parser.add_argument("--dry-run", action="store_true", help="Run without placing real orders")
    args = parser.parse_args()

    run(dry_run=args.dry_run)
