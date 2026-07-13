bl_info = {
    "name": "Jokero Blender MCP",
    "author": "Jokero",
    "version": (1, 0, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Sidebar > Jokero MCP",
    "description": "Connects Blender to Claude via a local MCP bridge server",
    "category": "Interface",
}

import bpy
import json
import socket
import threading
import time
import traceback


class MCPBridgeServer:
    def __init__(self, host="localhost", port=9876):
        self.host = host
        self.port = port
        self.running = False
        self.socket = None
        self.thread = None

    def start(self):
        if self.running:
            return
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((self.host, self.port))
        self.socket.listen(1)
        self.running = True
        self.thread = threading.Thread(target=self._serve, daemon=True)
        self.thread.start()
        print(f"[Jokero MCP] listening on {self.host}:{self.port}")

    def stop(self):
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except OSError:
                pass
        self.socket = None
        print("[Jokero MCP] stopped")

    def _serve(self):
        while self.running:
            try:
                self.socket.settimeout(1.0)
                try:
                    conn, _addr = self.socket.accept()
                except socket.timeout:
                    continue
                with conn:
                    self._handle_connection(conn)
            except OSError:
                break
            except Exception as exc:
                print(f"[Jokero MCP] server error: {exc}")
                time.sleep(1)

    def _handle_connection(self, conn):
        data = conn.recv(65536)
        if not data:
            return
        try:
            command = json.loads(data.decode("utf-8"))
        except json.JSONDecodeError:
            conn.sendall(json.dumps({"status": "error", "message": "invalid json"}).encode("utf-8"))
            return

        result_holder = {}
        done = threading.Event()

        def run_on_main():
            try:
                result_holder["result"] = execute_command(command)
            except Exception as exc:
                result_holder["error"] = f"{exc}\n{traceback.format_exc()}"
            done.set()
            return None

        bpy.app.timers.register(run_on_main, first_interval=0.0)
        done.wait(30)

        if "error" in result_holder:
            response = {"status": "error", "message": result_holder["error"]}
        elif not done.is_set():
            response = {"status": "error", "message": "timed out waiting for Blender main thread"}
        else:
            response = {"status": "success", "result": result_holder.get("result")}

        conn.sendall(json.dumps(response).encode("utf-8"))


def execute_command(command):
    cmd_type = command.get("type")
    params = command.get("params", {})

    if cmd_type == "get_scene_info":
        return get_scene_info()
    if cmd_type == "get_object_info":
        return get_object_info(params.get("name"))
    if cmd_type == "execute_code":
        return execute_code(params.get("code", ""))
    raise ValueError(f"Unknown command type: {cmd_type}")


def get_scene_info():
    scene = bpy.context.scene
    return {
        "scene_name": scene.name,
        "object_count": len(scene.objects),
        "objects": [
            {"name": obj.name, "type": obj.type, "location": list(obj.location)}
            for obj in scene.objects
        ],
        "blender_version": bpy.app.version_string,
    }


def get_object_info(name):
    obj = bpy.data.objects.get(name)
    if obj is None:
        raise ValueError(f"Object '{name}' not found")
    return {
        "name": obj.name,
        "type": obj.type,
        "location": list(obj.location),
        "rotation": list(obj.rotation_euler),
        "scale": list(obj.scale),
        "dimensions": list(obj.dimensions),
    }


def execute_code(code):
    namespace = {"bpy": bpy}
    exec(code, namespace)
    return {"executed": True}


mcp_server = MCPBridgeServer()


class JOKERO_MCP_PT_panel(bpy.types.Panel):
    bl_label = "Jokero MCP"
    bl_idname = "JOKERO_MCP_PT_panel"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Jokero MCP"

    def draw(self, context):
        layout = self.layout
        status = "Connected" if mcp_server.running else "Disconnected"
        layout.label(text=f"Status: {status}")
        if mcp_server.running:
            layout.label(text=f"Port: {mcp_server.port}")
            layout.operator("jokero_mcp.stop_server", text="Stop Server")
        else:
            layout.operator("jokero_mcp.start_server", text="Start Server")


class JOKERO_MCP_OT_start(bpy.types.Operator):
    bl_idname = "jokero_mcp.start_server"
    bl_label = "Start MCP Server"

    def execute(self, context):
        mcp_server.start()
        return {"FINISHED"}


class JOKERO_MCP_OT_stop(bpy.types.Operator):
    bl_idname = "jokero_mcp.stop_server"
    bl_label = "Stop MCP Server"

    def execute(self, context):
        mcp_server.stop()
        return {"FINISHED"}


classes = (
    JOKERO_MCP_PT_panel,
    JOKERO_MCP_OT_start,
    JOKERO_MCP_OT_stop,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    mcp_server.stop()
    for cls in classes:
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
