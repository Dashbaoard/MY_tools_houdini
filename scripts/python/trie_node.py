class TrieNode:
    def __init__(self, char):
        self.char = char
        self.is_end = False
        self.children = {}

class Trie(object):
    def __init__(self):
        self.root = TrieNode('')

    def insert(self, word):
        node = self.root

        for char in word:
            if char in node.children:
                node = node.children[char]
            else:
                new_node = TrieNode(char)
                node.children[char] = new_node
                node = new_node

        node.is_end = True

    def _dfs(self, node, prefix):
        if node.is_end:
            self.output.append((prefix + node.char))
        for child in node.children.values():
            self._dfs(child, prefix + node.char)

    def query(self, x):
        self.output = []
        node = self.root

        for char in x:
            if char in node.children:
                node = node.children[char]
            else:
                return []
        self._dfs(node, x[:-1])

        return sorted(self.output, key=lambda x: x[1], reverse=True)

if __name__ == '__main__':
    tr = Trie()
    tr.insert("amy")
    tr.insert("peter")
    tr.insert("hello")
    tr.insert("hey")
    tr.insert("hellothere")

    res = tr.query('he')
    print(res)


# class TrieNode:
#     def __init__(self, char):
#         self.char = char
#         self.is_end = False
#         self.children = {}
#
# class Trie(object):
#     def __init__(self):
#         self.root = TrieNode('')
#
#     def insert(self, word):
#         node = self.root
#         for char in word:
#             if char not in node.children:
#                 node.children[char] = TrieNode(char)
#             node = node.children[char]
#         node.is_end = True
#
#     def _dfs(self, node, prefix):
#         if node.is_end:
#             self.output.append(prefix + node.char)
#         for child in node.children.values():
#             self._dfs(child, prefix + node.char)
#
#     def query(self, x):
#         self.output = []
#         node = self.root
#         for char in x:
#             if char not in node.children:
#                 return []
#             node = node.children[char]
#         self._dfs(node, x)
#         return sorted(self.output, key=lambda x: x[1], reverse=True)
#
# if __name__ == '__main__':
#     tr = Trie()
#     tr.insert('amy')
#     tr.insert("peter")
#     tr.insert("hello")
#     tr.insert("hey")
#     tr.insert("hellothere")
#
#     res = tr.query('he')
#     print(res)