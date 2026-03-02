import os
# BUG 1: Hardcoded Secret
ADMIN_PASSWORD = "super-secret-12345" 

# BUG 2: Command Injection
def run_cmd(user_input):
    os.system("echo " + user_input)