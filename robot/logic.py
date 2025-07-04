#!/usr/bin/env python3
import os
import time
import subprocess
import tkinter as tk
from tkinter import filedialog
import pyautogui
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logic_automation.log'),
        logging.StreamHandler()
    ]
)

def notify(message):
    """Show notification using osascript"""
    subprocess.run(['osascript', '-e', f'display notification "{message}"'])

def force_quit_logic():
    """Force quit Logic Pro"""
    subprocess.run(['killall', 'Logic Pro'], stderr=subprocess.DEVNULL)
    time.sleep(2)

def select_folder():
    """Open folder selection dialog"""
    root = tk.Tk()
    root.withdraw()  # Hide the main window
    folder_path = filedialog.askdirectory(title="Select main folder with music subfolders:")
    return folder_path if folder_path else None

def find_and_click_change_project():
    """Find and click the Change Project button using AppleScript"""
    apple_script = '''
    tell application "System Events"
        tell process "Logic Pro"
            set foundButton to false
            set allButtons to every button of window 1
            repeat with btn in allButtons
                try
                    set btnTitle to ""
                    set btnName to ""
                    set btnDescription to ""
                    
                    try
                        set btnTitle to title of btn as string
                    end try
                    try
                        set btnName to name of btn as string
                    end try
                    try
                        set btnDescription to description of btn as string
                    end try
                    
                    if btnTitle contains "Change Project" or btnName contains "Change Project" or btnDescription contains "Change Project" then
                        click btn
                        set foundButton to true
                        exit repeat
                    end if
                end try
            end repeat
            return foundButton
        end tell
    end tell
    '''
    
    try:
        result = subprocess.run(['osascript', '-e', apple_script], 
                              capture_output=True, 
                              text=True)
        return "true" in result.stdout.lower()
    except Exception as e:
        logging.error(f"Error finding Change Project button: {str(e)}")
        return False

def process_folder(folder_path):
    """Process a single folder containing _mix.wav file"""
    try:
        # Check for _mix.wav file
        mix_files = [f for f in os.listdir(folder_path) if f.endswith('_mix.wav')]
        wav_files = [f for f in os.listdir(folder_path) if f.endswith('.wav')]
        
        if not mix_files:
            logging.info(f"❌ No _mix.wav file found in: {folder_path}")
            return
        
        if len(wav_files) > len(mix_files):
            logging.info(f"⏭️ Skipping {folder_path} - already has other .wav files")
            return
        
        mix_file = os.path.join(folder_path, mix_files[0])
        folder_name = os.path.basename(folder_path)
        
        logging.info(f"Processing: {folder_name}")
        
        # Force quit Logic Pro if running
        force_quit_logic()
        
        # Open Logic Pro with the mix file
        subprocess.run(['open', '-a', 'Logic Pro', mix_file])
        time.sleep(20)  # Wait for Logic to load
        
        # Check for Change Project button
        if not find_and_click_change_project():
            logging.warning("Change Project button not found, continuing anyway...")
        time.sleep(2)
        
        # GUI Automation sequence
        try:
            # Click on the track area
            pyautogui.rightClick(x=898, y=223)
            time.sleep(2)
            
            # Navigate to Stem Splitter
            pyautogui.press('s')
            time.sleep(1)
            pyautogui.press('enter')
            time.sleep(1)
            pyautogui.press('enter')
            time.sleep(1)
            
            logging.info(f"🔄 Stem Splitter started for: {folder_name}")
            time.sleep(240)  # Wait for processing
            
            logging.info(f"✅ Stem Splitter completed. Starting export: {folder_name}")
            
            # Export sequence
            pyautogui.hotkey('command', 'e')  # File > Export shortcut
            time.sleep(2)
            pyautogui.press('6')
            time.sleep(1)
            pyautogui.press('enter')
            time.sleep(1)
            pyautogui.press('enter')
            
            logging.info(f"📁 Export started for: {folder_name}")
            time.sleep(40)  # Wait for export
            
            # Close Logic Pro
            pyautogui.click(x=730, y=388)  # Click close button
            time.sleep(2)
            force_quit_logic()
            
            logging.info(f"✅ {folder_name} processed and exported!")
            
        except Exception as e:
            logging.error(f"Error during GUI automation: {str(e)}")
            force_quit_logic()
            return
            
    except Exception as e:
        logging.error(f"Error processing folder {folder_path}: {str(e)}")
        force_quit_logic()

def main():
    # Select main folder
    main_folder = select_folder()
    if not main_folder:
        logging.error("No folder selected. Exiting.")
        return
    
    # Get all subfolders
    subfolders = [os.path.join(main_folder, d) for d in os.listdir(main_folder) 
                 if os.path.isdir(os.path.join(main_folder, d))]
    
    # Process each subfolder
    for folder in subfolders:
        process_folder(folder)
        time.sleep(2)  # Small delay between folders
    
    logging.info("🎉 All files have been processed!")

if __name__ == "__main__":
    # Fail-safe for pyautogui
    pyautogui.FAILSAFE = True
    main() 