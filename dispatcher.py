import os
import time
import logging
import random
from datetime import datetime
from urllib.parse import quote
import pyautogui

def process_dispatch_queue(queue, wait_time, tab_close, close_time, cool_down, max_retries):
    """
    Processes the ordered execution priority object array queue securely
    using the native Windows WhatsApp Desktop Application via URI schemes.
    """
    success, failed, skipped = 0, 0, 0
    total = len(queue)
    
    # Establish a fresh text file log trail for Feature 3
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    today_str = datetime.now().strftime('%Y.%m.%d')
    receipt_log_path = f"{log_dir}/dispatch_receipts_{today_str}.txt"
    
    print(f"🚀 Actionable dispatch queue loaded: {total} items selected for delivery.")
    print("⏳ IMPORTANT: Ensure your Windows WhatsApp Desktop Application is open and authenticated.")
    input("👉 Bring the WhatsApp window to the background, then press ENTER to run...")
    
    for idx, item in enumerate(queue, start=1):
        name = item["party"]
        phone = item["phone"]
        msg = item["message"]
        
        if not phone or phone.strip() == "+":
            print(f"⏩ [{idx}/{total}] Skipping '{name}': Missing valid phone target configuration.")
            skipped += 1
            continue
            
        # Feature 2: Time-of-Day dynamic greeting insertion
        hour = datetime.now().hour
        if hour < 12:
            greeting = "☀️ *Good Morning!*"
        elif hour < 16:
            greeting = "📊 *Good Afternoon!*"
        else:
            greeting = "🌙 *Good Evening!*"
            
        final_msg = f"{greeting}\n\n{msg}"
            
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] [{idx}/{total}] Dispatched Target -> {name} ({phone})")
        
        for attempt in range(1, max_retries + 1):
            try:
                start = time.time()
                encoded_msg = quote(final_msg)
                whatsapp_uri = f"whatsapp://send/?phone={phone}&text={encoded_msg}"
                
                os.startfile(whatsapp_uri)
                time.sleep(max(5, wait_time))
                pyautogui.press('enter')
                
                elapsed = time.time() - start
                success += 1
                
                logging.info(f"SUCCESS | {name} | {phone} | Attempt {attempt}")
                
                # Feature 3: Append data instantly to our live audit ledger text file
                with open(receipt_log_path, "a", encoding="utf-8") as f:
                    f.write(f"[{datetime.now().strftime('%H:%M:%S')}] SENT | {name} ({phone})\n")
                
                remaining = total - idx
                
                # Feature 2: Add dynamic anti-block variance (+1 to +3 random seconds added to cool down)
                actual_cooldown = cool_down + random.randint(1, 3)
                eta = remaining * (elapsed + actual_cooldown)
                print(f"⏳ Dynamic ETA Remaining: {int(eta // 60)} min {int(eta % 60)} sec")
                
                if remaining > 0:
                    time.sleep(actual_cooldown)
                break
                
            except Exception as e:
                logging.warning(f"Attempt {attempt}/{max_retries} failed for {name}: {e}")
                if attempt < max_retries:
                    time.sleep(5)
                else:
                    failed += 1
                    logging.error(f"FAILED | {name} | {phone} | Exceeded limit bounds: {e}")
                    with open(receipt_log_path, "a", encoding="utf-8") as f:
                        f.write(f"[{datetime.now().strftime('%H:%M:%S')}] FAILED | {name} ({phone}) | Error: {str(e)}\n")
                    print(f"❌ Failed permanently after {max_retries} desktop processing loops.")
                    
    return success, failed, skipped
