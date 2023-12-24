import os
from typing import Literal

class RomfsNode():
    def __init__(self, node_type: Literal["dir", "file", "hlink", "block", "unknown"]):
        self.type = node_type
        self.children = []
        self.data = b""
        self.entry_start = -1
        self.name = ""

class RomfsParse():
    def __init__(self) -> None:
        pass
    
    @staticmethod
    def from_file(filename: str):
        with open(filename, "rb") as f:
            return RomfsParse.from_bytes(f.read())

    @staticmethod
    def read_volume_name(data: bytes):
        i = 16
        name = b""
        while data[i] != 0:
            name += data[i:i+1]
            i += 1
        if i % 16 == 0:
            return (i, name.decode("utf-8"))
        else:
            return ((i // 16 + 1) * 16, name.decode("utf-8"))

    @staticmethod
    def read_filename(data: bytes, entry_start):
        start = entry_start + 16
        filename_start = start
        name = b""
        while True:
            name += data[filename_start : filename_start + 16]
            if name.find(b"\x00") > -1:
                break
            filename_start += 16
        
        name = name[:name.find(b"\x00")]
        filename_end = start + len(name) + 1
        if filename_end % 16 == 0:
            return (filename_end, name.decode("utf-8"))
        else:
            return ((filename_end // 16 + 1) * 16, name.decode("utf-8"))

    @staticmethod
    def view_one_level(data: bytes, entry_start):
        nodes = []
        while entry_start != 0:
            next_entry = int.from_bytes(data[entry_start : entry_start + 4], byteorder="big")
            info = int.from_bytes(data[entry_start + 4 : entry_start + 8], byteorder="big")
            size = int.from_bytes(data[entry_start + 8 : entry_start + 12], byteorder="big")
            checksum = int.from_bytes(data[entry_start + 12 : entry_start + 16], byteorder="big")

            data_begin, filename = RomfsParse.read_filename(data, entry_start)

            # print(hex(data_begin), filename)

            filetype = next_entry & 0b111

            if filetype == 1:
                node = RomfsNode("dir")
            elif filetype == 2:
                node = RomfsNode("file")
            elif filetype == 0:
                node = RomfsNode("hlink")
            elif filetype == 4:
                node = RomfsNode("block")
            else:
                node = RomfsNode("unknown")
            node.entry_start = entry_start
            node.data = data[data_begin : data_begin + size]
            node.name = filename
            nodes.append(node)

            next_entry >>= 4
            next_entry <<= 4
            entry_start = next_entry
        
        return nodes

    @staticmethod
    def from_bytes(data: bytes):
        if data[:8] != b"-rom1fs-":
            raise TypeError("not a romfs bin")
        
        system_size = int.from_bytes(data[8 : 12], byteorder="big")

        entry_start, volume_name = RomfsParse.read_volume_name(data)

        root_node = RomfsNode("dir")
        root_node.name = volume_name
        root_node.entry_start = entry_start

        path_nodes = [root_node] # 获取根节点作为目录节点集中的第一个元素
        all_nodes = [root_node]
        while len(path_nodes) > 0:
            node = path_nodes.pop() # 从目录节点集中弹出一个元素
            node_entry = node.entry_start
            next_entry = int.from_bytes(data[node_entry + 4 : node_entry + 8], byteorder="big")
            once_nodes = RomfsParse.view_one_level(data, next_entry) # 遍历这个目录节点的所属文件
            all_nodes += once_nodes 
            node.children = once_nodes
            for _ in once_nodes:
                if _.type == "dir" and _.name != ".":
                    # 如果目录下还有子目录，添加到目录节点集
                    path_nodes.append(_)

        # 返回根节点与所有节点集
        return root_node, all_nodes

"""vela_misc.bin"""

# 只打印文件系统结构
def travel_print(root_node, depth=0):
    if (root_node.type == "dir" and root_node.name != ".") or (root_node.type == "file"):
        print(depth * "\t" + root_node.name)
    for c in root_node.children:
        travel_print(c, depth + 1)

# 提取文件系统并输出
def travel_output(root_node, prefix="."):
    path = os.path.join(prefix, root_node.name)
    if root_node.type == "file":
        f = open(path, "wb")
        f.write(root_node.data)
        f.flush()
        f.close()
    elif root_node.type == "dir" and root_node.name != ".":
        os.mkdir(path)
    
    for c in root_node.children:
        travel_output(c, path)

root_node, all_nodes = RomfsParse.from_file(r"vela_misc.bin")
# travel_output(root_node)
travel_print(root_node)
