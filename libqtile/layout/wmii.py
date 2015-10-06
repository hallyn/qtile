# Copyright (c) 2013 Mattias Svala
# Copyright (c) 2013 Tao Sauvage
# Copyright (c) 2014 ramnes
# Copyright (c) 2014 Sean Vig
# Copyright (c) 2014 dmpayton
# Copyright (c) 2014 dequis
# Copyright (c) 2014 Tycho Andersen
# Copyright (c) 2015 Serge Hallyn
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

from __future__ import division

import math
import os

from .base import Layout

# We have an array of columns.  Each columns is a dict containing
# width (in percent), rows (an array of rows), # and mode, which is
# either 'stack' or 'split'
#
# Each row is an array of clients

def swap(array, a, b):
    tmp = array[b]
    array[b] = array[a]
    array[a] = tmp

class Wmii(Layout):
    """
        This layout emulates wmii layouts.  The screen it split into
        columns, always starting with one.  A new window is created in
        the active window's column.  Windows can be shifted left and right.
        If there is no column when shifting, a new one is created.
        Each column can be stacked or divided (equally split).
    """
    defaults = [
        ("border_focus", "#ff5555", "Border colour for the focused window."),
        ("border_normal", "#000000", "Border colour for un-focused windows."),
        ("border_stack", "#ff00ff", "Border colour for un-focused stacked windows."),
        ("border_width", 1, "Border width."),
        ("name", "wmii", "Name of this layout."),
        ("margin", 0, "Margin of the layout"),
    ]

    def __init__(self, **config):
        Layout.__init__(self, **config)
        self.add_defaults(Wmii.defaults)
        self.current_window = None
        self.clients = []
        self.columns = [ { 'active': 0, 'width' : 100, 'mode': 'split', 'rows': [] } ]

    def info(self):
        d = Layout.info(self)
        d["current_window"] = self.current_window
        d["clients"] = [x.name for x in self.clients]
        return d

    def add_column(self, prepend, win):
        with open("/tmp/out", "a") as outfile:
            outfile.write("add_column called\n")
        # todo - how to properly apportion new widths?
        newwidth = (int) (100 / (len(self.columns) + 1))
        # we are only called if there already is a column, simplifies things
        for c in self.columns:
            c['width'] = newwidth
        c = { 'width': newwidth, 'mode': 'split', 'rows': [ win ] }
        if prepend:
            self.columns.insert(0, c)
        else:
            self.columns.append(c)

    def clone(self, group):
        c = Layout.clone(self, group)
        c.current_window = None
        c.clients = []
        c.columns = [ { 'active': 0, 'width' : 100, 'mode': 'split', 'rows': [] } ]
        return c

    def current_column(self):
        if self.current_window == None:
            return None
        for c in self.columns:
            if self.current_window in c['rows']:
                return c
        return None

    def add(self, client):
        self.clients.append(client)
        c = self.current_column()
        if c == None:
            c = self.columns[0]
        c['rows'].append(client)
        self.focus(client)

    def remove(self, client):
        if client not in self.clients:
            return
        self.clients.remove(client)
        if self.current_window != client:
            return
        self.current_window = None
        for c in self.columns:
            if client in c['rows']:
                ridx = c['rows'].index(client)
                cidx = self.columns.index(c)
                c['rows'].remove(client)
                if len(c['rows']) != 0:
                    if ridx > 0:
                        ridx -= 1
                    newclient = c['rows'][ridx]
                    self.focus(newclient)
                    return newclient
                # column is now empty, remove it and select the previous one
                self.columns.remove(c)
                newwidth = (int) (100 / len(self.columns))
                for c in self.columns:
                    c['width'] = newwidth
                if len(self.columns) == 1:
                    # there is no window at all
                    return None
                if cidx > 0:
                    cidx -= 1
                c = self.columns[cidx]
                rows = c['rows']
                newclient = rows[0]
                self.current_window = newclient
                self.group.focus(newclient)
                return newclient

    def focus(self, client):
        self.current_window = client
        for c in self.columns:
            if client in c['rows']:
                c['active'] = c['rows'].index(client)

    def configure(self, client, screen):
        show = True
        if client not in self.clients:
            return
        ridx = -1
        xoffset = int(screen.x)
        with open("/tmp/out", "a") as outfile:
            outfile.write("there are %d columns\n" % len(self.columns))
        for c in self.columns:
            if client in c['rows']:
                ridx = c['rows'].index(client)
                break
            xoffset += int(float(c['width']) * screen.width / 100.0)
        if ridx == -1:
            return
        cidx = self.columns.index(c)
        if client == self.current_window:
            px = self.group.qtile.colorPixel(self.border_focus)
        elif c['mode'] == "stack":
            px = self.group.qtile.colorPixel(self.border_stack)
        else:
            px = self.group.qtile.colorPixel(self.border_normal)
        if c['mode'] == 'split':
            oneheight = screen.height / len(c['rows'])
            yoffset = int(screen.y + oneheight * ridx)
            win_height = int(oneheight - 2 * self.border_width)
        else:  # stacked
            if c['active'] != c['rows'].index(client):
                show = False
            yoffset = int(screen.y) # todo - also add a titlebar for each stacked window?
            win_height = int(screen.height - 2 * self.border_width)
        win_width = int(float(c['width'] * screen.width / 100.0))
        with open("/tmp/out", "a") as outfile:
            outfile.write("configure: win_width is %d\n" % (win_width))
        win_width -= 2 * self.border_width

        if show:
            client.place(
                xoffset,
                yoffset,
                win_width,
                win_height,
                self.border_width,
                px,
                margin=self.margin,
            )
            client.unhide()
        else:
            client.hide()

    def cmd_toggle_split(self):
        c = self.current_column()
        if c['mode'] == "split":
            c['mode'] = "stack"
        else:
            c['mode'] = "split"

    def focus_next(self):
        self.cmd_down()
        return self.curent_window

    def focus_previous(self):
        self.cmd_up()
        return self.current_window

    def focus_first(self):
        c = self.columns[0]
        if len(c.rows) != 0:
            return c.rows[0]

    def focus_last(self):
        c = self.columns(len(self.columns) - 1)
        if len(c.rows) != 0:
            return c.rows[len(c.rows) - 1]


    def cmd_left(self):
        """
            Switch to the first window on prev column
        """
        with open("/tmp/out", "a") as outfile:
            outfile.write("cmd_left: called\n")
        c = self.current_column()
        cidx = self.columns.index(c)
        with open("/tmp/out", "a") as outfile:
            outfile.write("cmd_left: cidx is %d\n" % cidx)
        if cidx == 0:
            return
        cidx -= 1
        self.group.focus(self.columns[cidx]['rows'][0])
        with open("/tmp/out", "a") as outfile:
            outfile.write("cmd_left: cidx is now %d\n" % cidx)

    def cmd_right(self):
        """
            Switch to the first window on next column
        """
        c = self.current_column()
        cidx = self.columns.index(c)
        if cidx == len(self.columns) - 1:
            return
        cidx += 1
        self.group.focus(self.columns[cidx]['rows'][0])

    def cmd_up(self):
        """
            Switch to the previous window in current column
        """
        c = self.current_column()
        if c == None:
            return
        ridx = c['rows'].index(self.current_window)
        if c['mode'] == "split" and ridx == 0:
            return
        ridx -= 1
        client = c['rows'][ridx]
        self.group.focus(client)

    def cmd_down(self):
        """
            Switch to the next window in current column
        """
        c = self.current_column()
        if c == None:
            return
        ridx = c['rows'].index(self.current_window)
        if c['mode'] == "split" and ridx == len(c['rows']) - 1:
            return
        ridx += 1
        client = c['rows'][ridx]
        self.group.focus(client)

    cmd_next = cmd_down
    cmd_previous = cmd_up

    def cmd_shuffle_left(self):
        cur = self.current_window
        if cur == None:
            return
        for c in self.columns:
            if cur in c['rows']:
                with open("/tmp/out", "a") as outfile:
                    outfile.write("shuffle_left: found window\n")
                cidx = self.columns.index(c)
                with open("/tmp/out", "a") as outfile:
                    outfile.write("shuffle_left: cidx is %d\n" % (cidx))
                if cidx == 0:
                    if len(c['rows']) == 1:
                        return
                    c['rows'].remove(cur)
                    with open("/tmp/out", "a") as outfile:
                        outfile.write("shuffle_left: adding a column\n")
                    self.add_column(True, cur)
                    if len(c['rows']) == 0:
                        self.columns.remove(c)
                else:
                    with open("/tmp/out", "a") as outfile:
                        outfile.write("shuffle_left: adding to previous column\n")
                    c['rows'].remove(cur)
                    self.columns[cidx - 1]['rows'].append(cur)
                with open("/tmp/out", "a") as outfile:
                    outfile.write("shuffle_left: after removal, len rows is %d\n" % len(c['rows']))
                if len(c['rows']) == 0:
                    self.columns.remove(c)
                    newwidth = (int) (100 / len(self.columns))
                    with open("/tmp/out", "a") as outfile:
                        outfile.write("shuffle_left: after removal, newwidth is %d\n" % newwidth)
                    for c in self.columns:
                        c['width'] = newwidth
                self.group.focus(cur)
                return

    def cmd_shuffle_right(self):
        cur = self.current_window
        if cur == None:
            return
        for c in self.columns:
            if cur in c['rows']:
                cidx = self.columns.index(c)
                if cidx == len(self.columns) - 1:
                    if len(c['rows']) == 1:
                        return
                    c['rows'].remove(cur)
                    self.add_column(False, cur)
                    if len(c['rows']) == 0:
                        self.columns.remove(c)
                else:
                    c['rows'].remove(cur)
                    self.columns[cidx+1]['rows'].append(cur)
                if len(c['rows']) == 0:
                    self.columns.remove(c)
                    newwidth = (int) (100 / len(self.columns))
                    for c in self.columns:
                        c['width'] = newwidth
                self.group.focus(cur)
                return

    def cmd_shuffle_down(self):
        for c in self.columns:
            if self.current_window in c['rows']:
                r = c['rows']
                ridx = r.index(self.current_window)
                if ridx < len(r):
                    swap(r, ridx, ridx + 1)
                    client = r[ridx + 1]
                    self.focus(client)
                    self.group.focus(client)
                return

    def cmd_shuffle_up(self):
        for c in self.columns:
            if self.current_window in c['rows']:
                r = c['rows']
                ridx = r.index(self.current_window)
                if ridx > 0:
                    swap(r, ridx - 1, ridx)
                    client = r[ridx - 1]
                    self.focus(client)
                    self.group.focus(client)
                return
