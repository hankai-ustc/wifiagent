import wpactrl

class VAP():
    def __init__(self,ifname):
        self.ifname=ifname
        self.ctrl_iface="/var/run/hostapd/%s" %self.ifname
        self.wpa=self.start_wpa(self.ctrl_iface)

    def start_wpa(self,path):
        wpa=wpactrl.WPACtrl(path)
        return wpa

    def wpa_ctrl_close(self):
        self.wpa.close()

    def status(self):
        return self.wpa.status()

    def get_phy(self):
        return self.wpa.status().phy
    def get_channel(self):
        return self.wpa.status().channel

    def get_ssid(self):
        return self.wpa.get_config().ssid
    def get_bssid(self):
        return self.wpa.get_config().bssid

