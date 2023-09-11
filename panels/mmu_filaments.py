# Happy Hare MMU Software
# Display filaments loaded on each gate and allow editing of gate_map
#
# Copyright (C) 2023  moggieuk#6538 (discord)
#                     moggieuk@hotmail.com
#
import logging, gi, json

gi.require_version("Gtk", "3.0")

from gi.repository import Gtk, GLib, Pango, Gdk
from ks_includes.screen_panel import ScreenPanel
from panels.spoolman import SpoolmanSpool
from ks_includes.KlippyRest import KlippyRest

class Panel(ScreenPanel):
    apiClient: KlippyRest
    TOOL_UNKNOWN = -1
    TOOL_BYPASS = -2

    GATE_UNKNOWN = -1
    GATE_EMPTY = 0
    GATE_AVAILABLE = 1
    GATE_AVAILABLE_FROM_BUFFER = 2

    W3C_COLORS = ['aliceblue', 'antiquewhite', 'aqua', 'aquamarine', 'azure', 'beige', 'bisque', 'black', 'blanchedalmond', 'blue', 'blueviolet',
                  'brown', 'burlywood', 'cadetblue', 'chartreuse', 'chocolate', 'coral', 'cornflowerblue', 'cornsilk', 'crimson', 'cyan', 'darkblue',
                  'darkcyan', 'darkgoldenrod', 'darkgray', 'darkgreen', 'darkgrey', 'darkkhaki', 'darkmagenta', 'darkolivegreen', 'darkorange',
                  'darkorchid', 'darkred', 'darksalmon', 'darkseagreen', 'darkslateblue', 'darkslategray', 'darkslategrey', 'darkturquoise', 'darkviolet',
                  'deeppink', 'deepskyblue', 'dimgray', 'dimgrey', 'dodgerblue', 'firebrick', 'floralwhite', 'forestgreen', 'fuchsia', 'gainsboro',
                  'ghostwhite', 'gold', 'goldenrod', 'gray', 'green', 'greenyellow', 'grey', 'honeydew', 'hotpink', 'indianred', 'indigo', 'ivory',
                  'khaki', 'lavender', 'lavenderblush', 'lawngreen', 'lemonchiffon', 'lightblue', 'lightcoral', 'lightcyan', 'lightgoldenrodyellow',
                  'lightgray', 'lightgreen', 'lightgrey', 'lightpink', 'lightsalmon', 'lightseagreen', 'lightskyblue', 'lightslategray', 'lightslategrey',
                  'lightsteelblue', 'lightyellow', 'lime', 'limegreen', 'linen', 'magenta', 'maroon', 'mediumaquamarine', 'mediumblue', 'mediumorchid',
                  'mediumpurple', 'mediumseagreen', 'mediumslateblue', 'mediumspringgreen', 'mediumturquoise', 'mediumvioletred', 'midnightblue',
                  'mintcream', 'mistyrose', 'moccasin', 'navajowhite', 'navy', 'oldlace', 'olive', 'olivedrab', 'orange', 'orangered', 'orchid',
                  'palegoldenrod', 'palegreen', 'paleturquoise', 'palevioletred', 'papayawhip', 'peachpuff', 'peru', 'pink', 'plum', 'powderblue',
                  'purple', 'rebeccapurple', 'red', 'rosybrown', 'royalblue', 'saddlebrown', 'salmon', 'sandybrown', 'seagreen', 'seashell', 'sienna',
                  'silver', 'skyblue', 'slateblue', 'slategray', 'slategrey', 'snow', 'springgreen', 'steelblue', 'tan', 'teal', 'thistle', 'tomato',
                  'turquoise', 'violet', 'wheat', 'white', 'whitesmoke', 'yellow', 'yellowgreen']
    
    SPOOLMAN_SPOOLS =[]

    def __init__(self, screen, title):
        super().__init__(screen, title)
        self.apiClient = screen.apiclient

        self._materials = Gtk.ListStore(str, str)
        self._model = Gtk.ListStore(SpoolmanSpool.__gtype__)

        self.ui_sel_tool = 0

        grid = Gtk.Grid()
        grid.set_column_homogeneous(True)
        grid.set_row_spacing(10)

        mmu = self._printer.get_stat("mmu")

        self.spoolmanEnabled = self._printer.spoolman
        if self.spoolmanEnabled:
            self.load_spools()
        num_gates = len(mmu['gate_status'])
        for i in range(num_gates):
            status_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
            status = self.labels[f'status_{i}'] = self._gtk.Image()
            available = self.labels[f'available_{i}'] = Gtk.Label("Unknown")
            status_box.pack_start(status, True, True, 0)
            status_box.pack_start(available, True, True, 0)

            gate_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
            gate_icon = self.labels[f'gate_icon_{i}'] = self._gtk.Image('mmu_gate')
            gate_label = self.labels[f'gate_label_{i}'] = Gtk.Label(f'Gate #{i}')
            gate_box.pack_start(gate_icon, True, True, 0)
            gate_box.pack_start(gate_label, True, True, 0)

            color = self.labels[f'color_{i}'] = Gtk.Label(f'⬤')
            color.get_style_context().add_class("mmu_color_swatch")
            color.set_xalign(0.7)

            material = self.labels[f'material_{i}'] = Gtk.Label("n/a")
            material.get_style_context().add_class("mmu_material_text")
            material.set_xalign(0.1)

            tools = self.labels[f'tools_{i}'] = Gtk.Label("n/a")
            tools.get_style_context().add_class("mmu_gate_text")
            tools.set_xalign(0)

            edit = self.labels[f'edit_{i}'] = self._gtk.Button('mmu_gear', f'Edit', 'color4')
            edit.connect("clicked", self.select_edit, i)
            if self.spoolmanEnabled:
                spoolman = self.labels[f'spoolman_{i}'] = Gtk.Label("n/a")
                spoolman.get_style_context().add_class("mmu_material_text")
                spoolman.set_xalign(0.1)

                grid.attach(status_box, 0, i, 2, 1)
                grid.attach(gate_box,   2, i, 2, 1)
                grid.attach(color,      4, i, 2, 1)
                grid.attach(material,   6, i, 2, 1)
                grid.attach(spoolman,   8, i, 2, 1)
                grid.attach(tools,     11, i, 3, 1)
                grid.attach(edit,      14, i, 2, 1)
            else:
                grid.attach(status_box, 0, i, 3, 1)
                grid.attach(gate_box,   3, i, 3, 1)
                grid.attach(color,      6, i, 2, 1)
                grid.attach(material,   8, i, 3, 1)
                grid.attach(tools,     11, i, 3, 1)
                grid.attach(edit,      14, i, 2, 1)

        self.labels['unknown_icon'] = self._gtk.Image('mmu_unknown').get_pixbuf()
        self.labels['available_icon'] = self._gtk.Image('mmu_tick').get_pixbuf()
        self.labels['empty_icon'] = self._gtk.Image('mmu_cross').get_pixbuf()

        self.labels.update( {
            'status': self._gtk.Image(),
            'available': Gtk.Label("Unknown"),
            'gate_icon': self._gtk.Image('mmu_gate'),
            'gate_label': Gtk.Label('Gate #0'),
            'color': Gtk.Label('⬤'),
            'material': Gtk.Label('PLA'),
            'spoolman': Gtk.Label('Unknown'),
            'tools': Gtk.Label("n/a"),
            'save': self._gtk.Button('mmu_save', f'Save', 'color3'),
            'c_picker': self._gtk.Button('mmu_color_chooser', None, 'color1', scale=self.bts * 1.2),
            'c_selector': Gtk.ComboBoxText(),
            's_selector': Gtk.ComboBoxText(),
            'm_entry': Gtk.Entry(),
            'filament': Gtk.CheckButton(),
            'cancel': self._gtk.Button('cancel', None, 'color4', scale=self.bts * 1.2),
        } )

        edit_status_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        edit_status_box.pack_start(self.labels['status'], True, True, 0)
        edit_status_box.pack_start(self.labels['available'], True, True, 0)

        edit_gate_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        edit_gate_box.pack_start(self.labels['gate_icon'], True, True, 0)
        edit_gate_box.pack_start(self.labels['gate_label'], True, True, 0)

        self.labels['color'].get_style_context().add_class("mmu_color_swatch")
        self.labels['color'].set_xalign(0.7)

        self.labels['material'].get_style_context().add_class("mmu_material_text")
        self.labels['material'].set_xalign(0.1)

        self.labels['tools'].get_style_context().add_class("mmu_gate_text")
        self.labels['tools'].set_xalign(0)

        self.labels['save'].connect("clicked", self.select_save)

        self.labels['c_selector'].set_vexpand(False)
        for i in range(len(self.W3C_COLORS)):
            self.labels['c_selector'].append_text(self.W3C_COLORS[i])
        self.labels['c_selector'].connect("changed", self.select_w3c_color)

        if self.spoolmanEnabled:          
            self.labels['s_selector'].set_vexpand(False)
            self.labels['s_selector'].get_style_context()
            for i in range(len(self.SPOOLMAN_SPOOLS)):
                self.labels['s_selector'].append_text(str(self.SPOOLMAN_SPOOLS[i]['id']) + ':' + self.SPOOLMAN_SPOOLS[i]['filament']['name'])
            self.labels['s_selector'].connect("changed", self.select_spoolmon)
            self.labels['s_selector'].set_entry_text_column(0)

        self.labels['c_picker'].set_vexpand(False)
        self.labels['c_picker'].connect("clicked", self.select_color)

        self.labels['m_entry'].set_vexpand(False)
        self.labels['m_entry'].get_style_context().add_class("mmu_entry_text")
        self.labels['m_entry'].connect("button-press-event", self._screen.show_keyboard)
        self.labels['m_entry'].connect("focus-in-event", self._screen.show_keyboard)
        self.labels['m_entry'].connect("changed", self.select_material)
        self.labels['m_entry'].grab_focus_without_selecting()
        self.labels['m_entry'].set_max_length(6)

        self.labels['filament'].set_vexpand(False)
        self.labels['filament'].get_style_context().add_class("mmu_recover")
        self.labels['filament'].connect("notify::active", self.select_filament)
        self.labels['filament'].set_halign(Gtk.Align.CENTER)

        self.labels['cancel'].set_vexpand(False)
        self.labels['cancel'].connect("clicked", self.select_cancel_edit)

        current_gate_grid = Gtk.Grid()
        current_gate_grid.set_column_homogeneous(True)
        current_gate_grid.set_vexpand(False)

        current_gate_grid.attach(edit_status_box,         0, 0, 3, 1)
        current_gate_grid.attach(edit_gate_box,           3, 0, 3, 1)
        current_gate_grid.attach(self.labels['color'],    6, 0, 2, 1)
        current_gate_grid.attach(self.labels['material'], 8, 0, 3, 1)
        current_gate_grid.attach(self.labels['tools'],   11, 0, 3, 1)
        current_gate_grid.attach(self.labels['save'],    14, 0, 2, 1)

        edit_grid = Gtk.Grid()
        edit_grid.set_column_homogeneous(True)
        grid.set_row_spacing(0)
        grid.set_row_spacing(0)

        pad1 = Gtk.Box()
        pad1.set_vexpand(True)
        pad2 = Gtk.Box()
        pad2.set_vexpand(True)
        heading_color = Gtk.Label('Edit Filament Color')
        heading_color.set_yalign(1)
        heading_material = Gtk.Label('Material Type / Availability')
        heading_material.set_yalign(1)
        heading_spoolman = Gtk.Label('Spoolman Spool')
        heading_spoolman.set_yalign(1)

        edit_grid.attach(current_gate_grid,         0, 0, 16, 1)
        edit_grid.attach(pad1,                      0, 1, 16, 1)
        edit_grid.attach(heading_color,             0, 2,  8, 1)
        edit_grid.attach(heading_material,          8, 2,  8, 1)
        edit_grid.attach(self.labels['c_selector'], 0, 3,  6, 1)
        edit_grid.attach(self.labels['c_picker'],   6, 3,  2, 1)
        edit_grid.attach(Gtk.Box(),                 8, 3,  1, 1)
        edit_grid.attach(self.labels['m_entry'],    9, 3,  4, 1)
        edit_grid.attach(self.labels['filament'],  13, 3,  3, 1)
        if self.spoolmanEnabled:
            edit_grid.attach(heading_spoolman,          0, 4,  14, 1)
            edit_grid.attach(self.labels['s_selector'], 0, 5,  14, 1)
            edit_grid.attach(pad2,                      0, 6, 16, 1)

        else:
#        edit_grid.attach(self.labels['cancel'],    14, 3,  2, 1) # No room for this, but back button is good enough
            edit_grid.attach(pad2,                      0, 4, 16, 1)

        scroll = self._gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.add(grid)

        self.labels['layers'] = layers = Gtk.Notebook()
        layers.set_show_tabs(False)
        layers.insert_page(scroll, None, 0)
        layers.insert_page(edit_grid, None, 1)

        self.content.add(layers)
        self.gate_tool_map = self.build_gate_tool_map()

    def load_spools(self, data=None):
        hide_archived = self._config.get_config().getboolean("spoolman", "hide_archived", fallback=True)
        self._model.clear()
        del self.SPOOLMAN_SPOOLS[:]
        self.SPOOLMAN_SPOOLS=[]
        self._materials.clear()
        spools = self.apiClient.post_request("server/spoolman/proxy", json={
            "request_method": "GET",
            "path": f"/v1/spool?allow_archived={not hide_archived}",
        })
        if not spools or "result" not in spools:
            self._screen.show_error_modal("Exception when trying to fetch spools")
            return
        self.SPOOLMAN_SPOOLS = spools["result"]
        materials = []
        for spool in spools["result"]:
            spoolObject = SpoolmanSpool(**spool)
            self._model.append([spoolObject])
            if spoolObject.filament.material not in materials:
                materials.append(spoolObject.filament.material)

        materials.sort()
        self._materials.append([None, _("All")])
        for material in materials:
            self._materials.append([material, material])    

    def activate(self):
        if self.spoolmanEnabled:
            self.load_spools()
            self.labels['s_selector'].set_vexpand(False)
            self.labels['s_selector'].get_style_context()
            for i in range(len(self.SPOOLMAN_SPOOLS)):
                self.labels['s_selector'].append_text(str(self.SPOOLMAN_SPOOLS[i]['id']) + ':' + self.SPOOLMAN_SPOOLS[i]['filament']['name'])
            self.labels['s_selector'].connect("changed", self.select_spoolmon)
            self.labels['s_selector'].set_entry_text_column(0)

        mmu = self._printer.get_stat("mmu")
        gate_status = mmu['gate_status']
        gate_material = mmu['gate_material']
        if self.spoolmanEnabled:
            gate_spoolmanid = mmu['gate_spoolman']
        gate_color = mmu['gate_color']
        num_gates = len(gate_status)

        for i in range(num_gates):
            g_map = self.gate_tool_map[i]
            status_icon, status_str = self.get_status_details(gate_status[i])
            tool_str = self.get_tool_details(g_map['tools'])
            color = self.get_color_details(gate_color[i])

            self.labels[f'status_{i}'].clear()
            self.labels[f'status_{i}'].set_from_pixbuf(self.labels[f'{status_icon}'])
            self.labels[f'available_{i}'].set_label(status_str)
            self.labels[f'color_{i}'].override_color(Gtk.StateType.NORMAL, color)
            self.labels[f'material_{i}'].set_label(gate_material[i][:6])
            if self.spoolmanEnabled:
                self.labels[f'spoolman_{i}'].set_label(str(gate_spoolmanid [i]))
            self.labels[f'tools_{i}'].set_label(tool_str)

        self.labels['layers'].set_current_page(0) # Gate list layer

    def get_status_details(self, gate_status):
        if gate_status in (self.GATE_AVAILABLE, self.GATE_AVAILABLE_FROM_BUFFER):
            status_icon = 'available_icon'
            status_str = "Available"
        elif gate_status == self.GATE_EMPTY:
            status_icon = 'empty_icon'
            status_str = "Empty"
        else: 
            status_icon = 'unknown_icon'
            status_str = "Unknown"
        return status_icon, status_str

    def get_tool_details(self, tools):
        tool_str = ''
        if len(tools) > 0:
            tool_str = 'T' + ', '.join(map(str, tools[:2]))
            tool_str += ', ...' if len(tools) > 2 else ''
        return tool_str

    def get_color_details(self, gate_color):
        if gate_color == None:
            gate_color = ''
        color = Gdk.RGBA()
        if not Gdk.RGBA.parse(color, gate_color):
            Gdk.RGBA.parse(color, '#' + gate_color)
        return color

    # gate_tool_map = [ { 'tools': <list of tools mapped to this gate> } ]
    def build_gate_tool_map(self):
        gate_tool_map = []
        mmu = self._printer.get_stat("mmu")
        ttg_map = mmu['ttg_map']
        num_gates = len(ttg_map)
        for gate in range(num_gates):
            tools = []
            for tool in range(num_gates):
                if ttg_map[tool] == gate:
                    tools.append(tool)
            gate_tool_map.append({ 'tools': tools })
        return gate_tool_map

    def rgba_to_hex(self, rgba):
        red = int(rgba.red * 255)
        green = int(rgba.green * 255)
        blue = int(rgba.blue * 255)
        hex_string = "{:02x}{:02x}{:02x}".format(red, green, blue)
        return hex_string

    def process_update(self, action, data):
        if action == "notify_status_update":
            if 'configfile' in data:
                return
            elif 'mmu' in data:
                e_data = data['mmu']
                if 'ttg_map' in e_data or 'gate' in e_data or 'gate_status' in e_data or 'gate_material' in e_data or 'gate_spoolmanId' in e_data or 'gate_color' in e_data:
                    self.activate()

    def select_edit(self, widget, sel_gate):
        self.ui_sel_gate = sel_gate
        self.ui_gate_status = self._printer.get_stat('mmu', 'gate_status')[self.ui_sel_gate]
        self.ui_gate_material = self._printer.get_stat('mmu', 'gate_material')[self.ui_sel_gate]
        if self.spoolmanEnabled:
            self.ui_gate_spoolmanid = self._printer.get_stat('mmu', 'gate_spoolman')[self.ui_sel_gate]
        self.ui_gate_color = self._printer.get_stat('mmu', 'gate_color')[self.ui_sel_gate]
        self.labels['layers'].set_current_page(1) # Edit layer
        self.update_edited_gate()

        self.labels['m_entry'].set_text(self.ui_gate_material)
        if self.ui_gate_color in self.W3C_COLORS:
            self.labels['c_selector'].set_active(self.W3C_COLORS.index(self.ui_gate_color))
        spool = next(x for x in self.SPOOLMAN_SPOOLS if x['id'] == int(self.ui_gate_spoolmanid))
        if spool:
            self.labels['c_selector'].set_active(str(spool['id']) + ':' + spool['filament']['name'])
        self.labels['filament'].set_active(self.ui_gate_status in (self.GATE_AVAILABLE, self.GATE_AVAILABLE_FROM_BUFFER))

    def update_edited_gate(self):
        g_map = self.gate_tool_map[self.ui_sel_gate]
        status_icon, status_str = self.get_status_details(self.ui_gate_status)
        tool_str = self.get_tool_details(g_map['tools'])
        color = self.get_color_details(self.ui_gate_color)

        self.labels[f'status'].clear()
        self.labels[f'status'].set_from_pixbuf(self.labels[f'{status_icon}'])
        self.labels[f'available'].set_label(status_str)
        self.labels[f'color'].override_color(Gtk.StateType.NORMAL, color)
        self.labels[f'material'].set_label(self.ui_gate_material[:6])
        if self.spoolmanEnabled:
            self.labels[f'spoolman'].set_label(str(self.ui_gate_spoolmanid))
        self.labels[f'tools'].set_label(tool_str)

    def select_w3c_color(self, widget):
        self.ui_gate_color = self.labels['c_selector'].get_active_text()
        self.update_edited_gate()

    def select_spool(self, widget):
        width, height = self._screen.get_size()
        color = self.get_color_details(self.ui_gate_color)

        dialog = Gtk.ColorChooserDialog()
        dialog.set_rgba(color)
        dialog.set_use_alpha(False)
        dialog.get_style_context().add_class("dialog")
        dialog.set_default_size(width, height)
        dialog.set_resizable(False)
        dialog.set_transient_for(self._screen)
        dialog.set_modal(True)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            color = dialog.get_rgba()
            color_str = color.to_string()
            self.labels['s_selector'].set_active(-1)
            self.ui_gate_color = self.rgba_to_hex(color)
            self.update_edited_gate()
        dialog.destroy()

    def select_color(self, widget):
        width, height = self._screen.get_size()
        color = self.get_color_details(self.ui_gate_color)

        dialog = Gtk.ColorChooserDialog()
        dialog.set_rgba(color)
        dialog.set_use_alpha(False)
        dialog.get_style_context().add_class("dialog")
        dialog.set_default_size(width, height)
        dialog.set_resizable(False)
        dialog.set_transient_for(self._screen)
        dialog.set_modal(True)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            color = dialog.get_rgba()
            color_str = color.to_string()
            self.labels['c_selector'].set_active(-1)
            self.ui_gate_color = self.rgba_to_hex(color)
            self.update_edited_gate()
        dialog.destroy()

    def contains(list, filter):
        for x in list:
            if filter(x):
                return True
        return False
    
    def first(iterable, default=None):
        for item in iterable:
            return item
        return default

    def select_spoolmon(self, widget, icon_pos=None, event=None):
        text = self.labels['s_selector'].get_active_text()
        spoolId=text.split(':')
        spool = next(x for x in self.SPOOLMAN_SPOOLS if x['id'] == int(spoolId[0]))
        #spool = self.first(x for x in self.SPOOLMAN_SPOOLS if x['id'] == int(spoolId[0])) 
        logging.info(f"Selected Spoolman filament: {json.dumps(spool)}")
        if spool!=None:
            allowed_chars = set('+-_')
            material = ''.join(c for c in spool['filament']['material'] if c.isalnum() or c in allowed_chars)
            self.ui_gate_material = material
            self.ui_gate_spoolmanid = spoolId[0]
            self.labels['m_entry'].set_text(material)
            self.ui_gate_color = spool['filament']['color_hex']
            self.update_edited_gate()

    def select_material(self, widget, icon_pos=None, event=None):
        text = self.labels['m_entry'].get_text().upper()
        allowed_chars = set('+-_')
        material = ''.join(c for c in text if c.isalnum() or c in allowed_chars)
        self.ui_gate_material = material
        self.labels['m_entry'].set_text(material)
        self.update_edited_gate()

    def select_filament(self, widget, param):
        if self.labels['filament'].get_active():
            self.ui_gate_status = self.GATE_AVAILABLE
        else:
            self.ui_gate_status = self.GATE_EMPTY
        self.update_edited_gate()

    def select_save(self, widget):
        self.labels['s_selector'].set_active(-1)
        self.labels['c_selector'].set_active(-1)
        self._screen.remove_keyboard()
        if self.spoolmanEnabled:
            self._screen._ws.klippy.gcode_script(f"MMU_SET_GATE_MAP GATE={self.ui_sel_gate} COLOR={self.ui_gate_color} MATERIAL={self.ui_gate_material} SPOOLMANID={self.ui_gate_spoolmanid} AVAILABLE={self.ui_gate_status}")
        else:
            self._screen._ws.klippy.gcode_script(f"MMU_SET_GATE_MAP GATE={self.ui_sel_gate} COLOR={self.ui_gate_color} MATERIAL={self.ui_gate_material} AVAILABLE={self.ui_gate_status} QUIET=1")
        self.labels['layers'].set_current_page(0) # Gate list layer

    def select_cancel_edit(self, widget):
        self._screen.remove_keyboard()
        self.labels['layers'].set_current_page(0) # Gate list layer

