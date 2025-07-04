#!/usr/bin/env python3
import os
import time
import subprocess
import asyncio
import pyautogui
import logging
import json
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('robot_automation.log'),
        logging.StreamHandler()
    ]
)

class LogicRobot:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        # Fail-safe for pyautogui
        pyautogui.FAILSAFE = True
        
    async def notify(self, message: str):
        """Show notification using osascript"""
        try:
            subprocess.run(['osascript', '-e', f'display notification "{message}"'])
        except Exception as e:
            self.logger.error(f"Error sending notification: {str(e)}")

    async def force_quit_logic(self):
        """Force quit Logic Pro"""
        try:
            subprocess.run(['killall', 'Logic Pro'], stderr=subprocess.DEVNULL)
            await asyncio.sleep(2)
        except Exception as e:
            self.logger.error(f"Error force quitting Logic Pro: {str(e)}")

    async def focus_logic_pro(self) -> bool:
        """Focus Logic Pro window using AppleScript"""
        apple_script = '''
        tell application "Logic Pro"
            activate
        end tell
        '''
        try:
            subprocess.run(['osascript', '-e', apple_script])
            await asyncio.sleep(1)  # Wait for window to focus
            return True
        except Exception as e:
            self.logger.error(f"Error focusing Logic Pro: {str(e)}")
            return False

    async def move_logic_to_current_space(self) -> bool:
        """Move Logic Pro window to current space using AppleScript"""
        apple_script = '''
        tell application "System Events"
            tell process "Logic Pro"
                set frontmost to true
                if exists window 1 then
                    tell window 1
                        set position to {0, 0}
                    end tell
                end if
            end tell
        end tell
        '''
        try:
            subprocess.run(['osascript', '-e', apple_script])
            await asyncio.sleep(1)  # Wait for window to move
            return True
        except Exception as e:
            self.logger.error(f"Error moving Logic Pro window: {str(e)}")
            return False

    async def move_to_space_one(self) -> bool:
        """Move terminal and Logic Pro to Space 1"""
        apple_script = '''
        tell application "System Events"
            -- Move terminal to Space 1
            tell application "Terminal"
                activate
            end tell
            keystroke "1" using {control down}
            delay 1
            
            -- Move Logic Pro to Space 1 if it exists
            if exists process "Logic Pro" then
                tell process "Logic Pro"
                    set frontmost to true
                end tell
            end if
            
            -- Ensure we're in Space 1
            keystroke "1" using {control down}
            delay 1
        end tell
        '''
        try:
            subprocess.run(['osascript', '-e', apple_script])
            await asyncio.sleep(2)  # Wait for space switch
            return True
        except Exception as e:
            self.logger.error(f"Error moving to Space 1: {str(e)}")
            return False

    async def ensure_logic_pro_ready(self) -> bool:
        """Ensure Logic Pro is focused and in Space 1"""
        try:
            # First move everything to Space 1
            if not await self.move_to_space_one():
                return False
                
            # Then focus Logic Pro
            if not await self.focus_logic_pro():
                return False
                
            # Move window to top-left corner to ensure visibility
            apple_script = '''
            tell application "System Events"
                tell process "Logic Pro"
                    set frontmost to true
                    if exists window 1 then
                        tell window 1
                            set {position, size} to {{0, 0}, {1920, 1080}}
                        end tell
                    end if
                end tell
            end tell
            '''
            subprocess.run(['osascript', '-e', apple_script])
            await asyncio.sleep(2)  # Wait for window to stabilize
            return True
        except Exception as e:
            self.logger.error(f"Error preparing Logic Pro window: {str(e)}")
            return False

    async def find_and_click_change_project(self) -> bool:
        """Find and click the Change Project button using AppleScript"""
        apple_script = '''
        tell application "System Events"
            tell process "Logic Pro"
                set frontmost to true
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
            self.logger.error(f"Error finding Change Project button: {str(e)}")
            return False

    async def process_audio_file(self, file_path: str, folder_name: str) -> Dict[str, Any]:
        """Process a single audio file with Logic Pro automation"""
        try:
            self.logger.info(f"Starting processing: {folder_name}")
            
            # First move to Space 1
            if not await self.move_to_space_one():
                return {
                    "status": "error",
                    "folder": folder_name,
                    "file": file_path,
                    "error": "Failed to move to Space 1",
                    "message": "Could not switch to correct desktop space"
                }
            
            # Force quit Logic Pro if running
            await self.force_quit_logic()
            
            # Open Logic Pro with the mix file
            subprocess.run(['open', '-a', 'Logic Pro', file_path])
            await asyncio.sleep(10)  # Wait for Logic to load
            
            # Ensure Logic Pro is ready for interaction in Space 1
            if not await self.ensure_logic_pro_ready():
                return {
                    "status": "error",
                    "folder": folder_name,
                    "file": file_path,
                    "error": "Failed to prepare Logic Pro window",
                    "message": "Could not focus or move Logic Pro window to Space 1"
                }
            
            # Check for Change Project button
            if not await self.find_and_click_change_project():
                self.logger.warning("Change Project button not found, continuing anyway...")
            await asyncio.sleep(2)
            
            # Ensure we're still in Space 1 before GUI automation
            await self.move_to_space_one()
            await self.ensure_logic_pro_ready()
            
            # GUI Automation sequence
            try:
                # Click on the track area
                pyautogui.rightClick(x=898, y=223)
                await asyncio.sleep(2)
                
                # Navigate to Stem Splitter
                pyautogui.press('s')
                await asyncio.sleep(1)
                pyautogui.press('enter')
                await asyncio.sleep(1)
                pyautogui.press('enter')
                await asyncio.sleep(1)
                
                self.logger.info(f"🔄 Stem Splitter started for: {folder_name}")
                await asyncio.sleep(240)  # Wait for processing
                
                # Ensure we're in Space 1 before export
                await self.move_to_space_one()
                await self.ensure_logic_pro_ready()
                
                self.logger.info(f"✅ Stem Splitter completed. Starting export: {folder_name}")
                
                # Export sequence
                pyautogui.hotkey('command', 'e')  # File > Export shortcut
                await asyncio.sleep(2)
                pyautogui.press('A')
                await asyncio.sleep(1)
                pyautogui.press('enter')
                await asyncio.sleep(1)
                pyautogui.press('enter')
                
                self.logger.info(f"📁 Export started for: {folder_name}")
                await asyncio.sleep(40)  # Wait for export
                
                # Ensure we're in Space 1 before closing
                # await self.move_to_space_one()
                # await self.ensure_logic_pro_ready()
                
                # Close Logic Pro
                pyautogui.click(x=730, y=388)  # Click close button
                await asyncio.sleep(2)
                await self.force_quit_logic()
                
                self.logger.info(f"✅ {folder_name} processed and exported!")
                
                return {
                    "status": "success",
                    "folder": folder_name,
                    "file": file_path,
                    "message": "Processing completed successfully"
                }
                
            except Exception as e:
                self.logger.error(f"Error during GUI automation: {str(e)}")
                await self.force_quit_logic()
                return {
                    "status": "error",
                    "folder": folder_name,
                    "file": file_path,
                    "error": str(e),
                    "message": "GUI automation failed"
                }
                
        except Exception as e:
            self.logger.error(f"Error processing file {file_path}: {str(e)}")
            await self.force_quit_logic()
            return {
                "status": "error",
                "folder": folder_name,
                "file": file_path,
                "error": str(e),
                "message": "Processing failed"
            }

    async def verify_export(self, folder_name: str) -> bool:
        """Verify if files were exported correctly to Music/Logic folder"""
        try:
            logic_folder = "/Users/moises/Music/Logic"
            
            if not os.path.exists(logic_folder):
                self.logger.error(f"Logic export folder does not exist: {logic_folder}")
                return False
            
            # Look for exported files with the folder name
            exported_files = []
            for file in os.listdir(logic_folder):
                print("File: ", file)
                if folder_name.lower() in file.lower() and file.endswith('.wav'):
                    exported_files.append(file)
            
            if len(exported_files) > 0:
                self.logger.info(f"Found {len(exported_files)} exported files for {folder_name}")
                return True
            else:
                self.logger.error(f"No exported files found for {folder_name} in {logic_folder}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error verifying export: {str(e)}")
            return False

    async def process_folder(self, folder_path: str, folder_name: str = None) -> Dict[str, Any]:
        """Process a folder containing _mix.wav file"""
        try:
            if not folder_name:
                folder_name = os.path.basename(folder_path)
            
            # Check for _mix.wav file
            mix_files = [f for f in os.listdir(folder_path) if f.endswith('_mix.wav')]
            wav_files = [f for f in os.listdir(folder_path) if f.endswith('.wav')]
            
            if not mix_files:
                return {
                    "status": "skipped",
                    "folder": folder_name,
                    "message": "No _mix.wav file found"
                }
            
            if len(wav_files) > len(mix_files):
                return {
                    "status": "skipped",
                    "folder": folder_name,
                    "message": "Already has other .wav files"
                }
            
            mix_file = os.path.join(folder_path, mix_files[0])
            result = await self.process_audio_file(mix_file, folder_name)
            
            # If processing was successful, verify export
            if result["status"] == "success":
                if await self.verify_export(folder_name):
                    result["export_verified"] = True
                    result["message"] = "Processing and export completed successfully"
                else:
                    result["status"] = "error"
                    result["error"] = "Export verification failed - files not found in Logic folder"
                    result["export_verified"] = False
                    result["message"] = "Processing completed but export verification failed"
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error processing folder {folder_path}: {str(e)}")
            return {
                "status": "error",
                "folder": folder_name or os.path.basename(folder_path),
                "error": str(e),
                "message": "Folder processing failed"
            }

# Robot will be called by the worker, no main needed 