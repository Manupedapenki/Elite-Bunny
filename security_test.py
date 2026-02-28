import os
# BUG 1: Hardcoded secret (The bot should catch this)
ADMIN_TOKEN = "secret_998877665544" 

# BUG 2: Command Injection (The bot should catch this)
def run_user_cmd(cmd):
    os.system("echo " + cmd)