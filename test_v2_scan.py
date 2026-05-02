#!/usr/bin/env python3
import asyncio
import json
import httpx
import time

async def test_v2_scan():
    """Test v2 scan API and poll for results."""
    async with httpx.AsyncClient() as client:
        # Start scan
        print("Starting v2 scan for snapdeal.com...")
        resp = await client.post(
            "http://localhost:8765/api/v2/scan",
            json={"domain": "snapdeal.com", "quick": False}
        )
        job_data = resp.json()
        job_id = job_data.get("job_id")
        print(f"Job ID: {job_id}\n")
        
        # Poll for results
        all_emails = []
        start_time = time.time()
        poll_count = 0
        
        for i in range(18):  # 18 * 10s = 180s = 3 minutes
            await asyncio.sleep(10)
            poll_count += 1
            
            resp = await client.get(f"http://localhost:8765/api/v2/result/{job_id}")
            data = resp.json()
            
            status = data.get("status")
            emails = data.get("emails", [])
            
            elapsed = time.time() - start_time
            new_emails = [e for e in emails if e not in all_emails]
            all_emails = emails
            
            print(f"[{elapsed:6.0f}s] Poll #{poll_count}: {len(emails)} emails ({len(new_emails)} new), status={status}")
            
            if new_emails:
                for email in new_emails[:3]:
                    print(f"          + {email}")
            
            if status in ("COMPLETE", "FAILED"):
                print(f"\nScan {status}")
                break
        
        print(f"\nFinal result: {len(all_emails)} emails found")
        if all_emails:
            print("All emails:")
            for email in all_emails:
                print(f"  - {email}")

asyncio.run(test_v2_scan())
