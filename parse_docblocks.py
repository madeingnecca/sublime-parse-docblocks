import sublime_plugin
import re
from functools import cmp_to_key

RE_DOCBLOCK_COMMENT = '^( |\t)*?/\*(.|\n)*?\*/'
RE_DOCBLOCK_TAG = '^(\t*?) ?\* @([^\s]+)\s+([^\s]+)?'
TAGS_ORDER = ['package', 'module', 'submodule', 'function', 'class', 'method']


class ParseDocblocksCommand(sublime_plugin.TextCommand):

    def parse_blocks(self):
        bid = 1
        blocks = []
        regions = self.view.find_all(RE_DOCBLOCK_COMMENT)

        for r in regions:
            region_string = self.view.substr(self.view.line(r))
            lines = region_string.splitlines()

            # Prepare the block.
            block = {}
            block['tags'] = {}
            block['path'] = []
            block['region'] = r

            for line in lines:
                match = re.search(RE_DOCBLOCK_TAG, line)
                if match is not None:
                    depth = 0
                    if match.group(1) is not None:
                        depth = len(match.group(1))

                    tag_name = match.group(2)
                    if tag_name in TAGS_ORDER:
                        tag_value = match.group(3)
                        block['tags'][tag_name] = tag_value

                    block['depth'] = depth

            # Skip if no tags were found.
            if not block['tags']:
                continue

            for index, tag_name in enumerate(TAGS_ORDER):
                if tag_name in block['tags']:
                    block['path'].append(block['tags'][tag_name])

            block['id'] = bid
            bid += 1

            blocks.append(block)

        return blocks

    def build_hierarchy(self, blocks):
        block_index = {}
        last_by_depth = {}

        for block in blocks:
            block_index[block['id']] = block

        for block in blocks:
            bid = block['id']
            depth = block['depth']
            parent_depth = depth - 1
            parent_block = None

            # Search for my parent block, if any.
            # Note: parent block could have a depth different
            # from my depth minus 1.
            while parent_depth not in last_by_depth and parent_depth >= 0:
                parent_depth -= 1

            if parent_depth >= 0 and parent_depth != depth:
                parent_block = block_index[last_by_depth[parent_depth]]

            if parent_block is not None:
                temp_path = parent_block['path'].copy()
                temp_path.extend(block['path'])
                block['path'] = temp_path

            last_by_depth[depth] = bid

    def build_quicklist(self, blocks):
        self.build_hierarchy(blocks)

        for block in blocks:
            block['path_string'] = '.'.join(block['path'])

        # Sort by "path_string" property.
        sorted_blocks = sorted(blocks, key=lambda block: block['path_string'])

        quicklist = {}
        quicklist['list'] = []
        quicklist['sorted_blocks'] = sorted_blocks

        for block in sorted_blocks:
            quicklist['list'].append(block['path_string'])

        return quicklist

    def run(self, edit):
        blocks = self.parse_blocks()
        hierarchy = self.build_quicklist(blocks)

        def goto_block(index):
            if index is not -1:
                block = hierarchy['sorted_blocks'][index]
                self.view.sel().clear()
                self.view.sel().add(block['region'])
                self.view.show(block['region'])

        self.view.window().show_quick_panel(hierarchy['list'], goto_block)
