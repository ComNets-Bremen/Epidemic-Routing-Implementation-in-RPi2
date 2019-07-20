#It executes commands in the shell and it returns the output
from subprocess import check_output
#Input: List of strings example: ['ls','source'] is equal to "ls source"
#Output: String with the command's returned information
def write_read_cmd(list_command):
    try:
        out = check_output(list_command)
    except:
        out=bytes(0); 
    return out;
