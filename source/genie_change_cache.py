class ChangeCache(object):
    def __init__(self):
        self.wiring = None
        self.detector = None
        self.spectra = None
        self.mon_spect = None
        self.mon_from = None
        self.mon_to = None
        self.dae_sync = None
        self.tcb_file = None
        self.tcb_tables = []
        self.smp_veto = None
        self.ts2_veto = None
        self.hz50_veto = None
        self.ext0_veto = None
        self.ext1_veto = None
        self.ext2_veto = None
        self.ext3_veto = None
        self.fermi_veto = None
        self.fermi_delay = None
        self.fermi_width = None
        self.periods_soft_num = None
        self.periods_type = None
        self.periods_src = None
        self.periods_file = None
        self.periods_seq = None
        self.periods_delay = None
        self.periods_settings = []
        
    def set_monitor(self, spec, low, high):
        self.mon_spect = spec
        self.mon_from = low
        self.mon_to = high
        
    def clear_vetos(self):
        self.smp_veto = 0
        self.ts2_veto = 0
        self.hz50_veto = 0
        self.ext0_veto = 0
        self.ext1_veto = 0
        self.ext2_veto = 0
        self.ext3_veto = 0
        
    def set_fermi(self, enable, delay=1.0, width=1.0):
        self.fermi_veto = 1
        self.fermi_delay = delay
        self.fermi_width = width
        
    def change_dae_settings(self, root):
        changed = False
        if self.wiring is not None:
            self._change_xml(root, 'String', 'Wiring Table', self.wiring)
            changed = True
        if self.detector is not None:
            self._change_xml(root, 'String', 'Detector Table', self.detector)
            changed = True
        if self.spectra is not None:
            self._change_xml(root, 'String', 'Spectra Table', self.spectra)
            changed = True
        if self.mon_spect is not None:
            self._change_xml(root, 'I32', 'Monitor Spectrum', self.mon_spect)
            changed = True
        if self.mon_from is not None:
            self._change_xml(root, 'DBL', 'from', self.mon_from)
            changed = True
        if self.mon_to is not None:
            self._change_xml(root, 'DBL', 'to', self.mon_to)
            changed = True
        if self.dae_sync is not None:
            self._change_xml(root, 'EW', 'DAETimingSource', self.dae_sync)
            changed = True
        if self.fermi_veto is not None:
            self._change_xml(root, 'EW', ' Fermi Chopper Veto', self.fermi_veto)
            self._change_xml(root, 'DBL', 'FC Delay', self.fermi_delay)
            self._change_xml(root, 'DBL', 'FC Width', self.fermi_width)
            changed = True
            
        changed = self._change_vetos(root, changed)
        return changed
        
    def _change_vetos(self, root, changed):
        if self.smp_veto is not None:
            self._change_xml(root, 'EW', 'SMP (Chopper) Veto', self.smp_veto)
            changed = True
        if self.ts2_veto is not None:
            self._change_xml(root, 'EW', ' TS2 Pulse Veto', self.ts2_veto)
            changed = True
        if self.hz50_veto is not None:
            self._change_xml(root, 'EW', ' ISIS 50Hz Veto', self.hz50_veto)
            changed = True
        if self.ext0_veto is not None:
            self._change_xml(root, 'EW', 'Veto 0', self.ext0_veto)
            changed = True
        if self.ext1_veto is not None:
            self._change_xml(root, 'EW', 'Veto 1', self.ext1_veto)
            changed = True
        if self.ext2_veto is not None:
            self._change_xml(root, 'EW', 'Veto 2', self.ext2_veto)
            changed = True
        if self.ext3_veto is not None:
            self._change_xml(root, 'EW', 'Veto 3', self.ext3_veto)
            changed = True
        return changed
        
    def change_tcb_settings(self, root):
        changed = False
        if self.tcb_file is not None:
            self._change_xml(root, 'String', 'Time Channel File', self.tcb_file)
            changed = True
        changed = self._change_tcb_table(root, changed)
        return changed
            
    def _change_tcb_table(self, root, changed):
        for row in self.tcb_tables:
            regime = str(row[0])
            trange = str(row[1])
            self._change_xml(root, 'DBL', 'TR%s From %s' % (regime, trange), row[2])
            self._change_xml(root, 'DBL', 'TR%s To %s' % (regime, trange), row[3])
            self._change_xml(root, 'DBL', 'TR%s Steps %s' % (regime, trange), row[4])
            self._change_xml(root, 'U16', 'TR%s In Mode %s' % (regime, trange), row[5])
            changed = True
        return changed
            
    def change_period_settings(self, root):
        changed = False
        if self.periods_type is not None:
            self._change_xml(root, 'EW', 'Period Type', self.periods_type)
            changed = True
        if self.periods_soft_num is not None:
            self._change_xml(root, 'I32', 'Number Of Software Periods', self.periods_soft_num)
            changed = True
        if self.periods_src is not None:
            self._change_xml(root, 'EW', 'Period Setup Source', self.periods_src)
            changed = True
        if self.periods_seq is not None:
            self._change_xml(root, 'DBL', 'Hardware Period Sequences', self.periods_seq)
            changed = True
        if self.periods_delay is not None:
            self._change_xml(root, 'DBL', 'Output Delay (us)', self.periods_delay)
            changed = True
        if self.periods_file is not None:
            self._change_xml(root, 'String', 'Period File', self.periods_file)
            changed = True
        if self.periods_settings is not None:
            self._change_period_table(root, self.periods_settings)
            changed = True
        return changed
            
    def _change_period_table(self, root, changed):
        for row in self.periods_settings:
            period = row[0]
            ptype = row[1]
            frames = row[2]
            output = row[3]
            label = row[4]
            if ptype is not None:
                self._change_xml(root, 'EW', 'Type %s' % period, ptype)
                changed = True
            if frames is not None:
                self._change_xml(root, 'I32', 'Frames %s' % period, frames)
                changed = True
            if output is not None:
                self._change_xml(root, 'U16', 'Output %s' % period, output)
                changed = True
            if label is not None:
                self._change_xml(root, 'String', 'Label %s' % period, label)
                changed = True
        return changed
            
    def _change_xml(self, xml, node, name, value):
        for top in xml.iter(node):
            n = top.find('Name')
            if n.text == name:
                v = top.find('Val')
                v.text = str(value)
                break