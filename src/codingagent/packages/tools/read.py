import logging
import subprocess
import json

from mcp.server.fastmcp import FastMCP

# initialise FastMCP server
mcp = FastMCP("read", log_level="CRITICAL")

@mcp.tool()
def read_file(file_path: str, offset = 0, limit = 20000) -> str:
    """Reads a file from the local filesystem. You can access any file directly by using this tool.
       Assume this tool is able to read all files on the machine. If the User provides a path to a file assume that path is valid. It is okay to read a file that does not exist; an error will be returned.

       Usage:
       - The file_path parameter must be an absolute path, not a relative path
       - By default, it reads up to 2000 lines starting from the beginning of the file
       - You can optionally specify a line offset and limit (especially handy for long files), but it's recommended to read the whole file by not providing these parameters
       - Results are returned using cat -n format, with line numbers starting at 1
       - You have the capability to call multiple tools in a single response. It is always better to speculatively read multiple files as a batch that are potentially useful. 
       - We can not read image files (PNG, JPG etc.) or PDF files, you will receive an error if you attempt to read these files.
       - If the file's last line only contains the word '__TRUNCATED__' communicate this to the user, only fetch more if the user asks you to do so.
    """

    # validate file extension
    # TODO: Should probably use file metadata instead of extension (bunch of edge cases)
    if file_path.endswith(".png") or file_path.endswith(".jpg") or file_path.endswith(".pdf"):
        json.dumps({"error": "file ending with .png, .jpg or .pdf can not be read"})

    try:
        result = subprocess.run(
            ["cat", "-n", file_path],
            capture_output=True,
            text=True,
        ) 

        # if it was successful then capture output and send back
        if result.returncode == 0:
            output = result.stdout

            # use offset if provided:
            if offset != 0:
                output = output[offset:]

            # ensure output is not too long to prevent limiting context window
            if len(output) > limit:
                output = output[:limit]
                output = output + "\n__TRUNCATED__\n"

            return output
        else:
            raise ValueError(f"something went wrong: {result.stderr}")
    except Exception as e:
        return json.dumps({"error": str(e)})

if __name__ == "__main__":
    mcp.run()