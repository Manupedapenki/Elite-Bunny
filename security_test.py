import os
# BUG 1: Hardcoded secret
ADMIN_TOKEN = "secret_998877665544" 

# BUG 2: Command Injection
def run_user_cmd(cmd):
    os.system("echo " + cmd)