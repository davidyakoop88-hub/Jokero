import json
import socket

from mcp.server.fastmcp import FastMCP

HOST = "localhost"
PORT = 9876

mcp = FastMCP("jokero-blender")


def _send_command(command_type: str, params: dict | None = None) -> dict:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(30)
        try:
            sock.connect((HOST, PORT))
        except (ConnectionRefusedError, socket.timeout) as exc:
            raise RuntimeError(
                "Could not reach the Jokero MCP Blender addon on "
                f"{HOST}:{PORT}. Make sure Blender is running with the "
                "addon enabled and the server started."
            ) from exc

        sock.sendall(json.dumps({"type": command_type, "params": params or {}}).encode("utf-8"))

        data = b""
        while True:
            chunk = sock.recv(65536)
            if not chunk:
                break
            data += chunk
            try:
                response = json.loads(data.decode("utf-8"))
                break
            except json.JSONDecodeError:
                continue
        else:
            raise RuntimeError("Blender addon closed the connection without sending a response")

    if response.get("status") == "error":
        raise RuntimeError(response.get("message", "Unknown Blender error"))
    return response.get("result")


@mcp.tool()
def get_scene_info() -> dict:
    """Get the current Blender scene name, object count, object list and Blender version."""
    return _send_command("get_scene_info")


@mcp.tool()
def get_object_info(name: str) -> dict:
    """Get location, rotation, scale and dimensions for a named object in the Blender scene."""
    return _send_command("get_object_info", {"name": name})


@mcp.tool()
def execute_blender_code(code: str) -> dict:
    """Execute arbitrary Python code inside Blender's process (has access to bpy)."""
    return _send_command("execute_code", {"code": code})


if __name__ == "__main__":
    mcp.run()
