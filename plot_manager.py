import matplotlib.pyplot as plt


class PlotManager:

    def __init__(self):
        # figの作成
        self.fig = plt.figure()
        self.fig.subplots_adjust(left=0.1, right=0.96, bottom=0.15, top=0.96)
        # 座標軸の作成
        self.ax = self.fig.add_subplot(1, 1, 1)
        plt.rcParams.update({"font.size": 10})
        self.config = {"linewidth": 0.5}
        self.filepath = None
        self.df = None

    def set_plot_style(self):
        _fontsize = 10
        for spine in plt.gca().spines.values():
            spine.set_linewidth(0.4)
        plt.gca().tick_params(axis='both',
                              which='major',
                              top=True,
                              right=True,
                              width=0.4,
                              direction='in',
                              length=4.0)
        plt.gca().tick_params(axis='both',
                              which='minor',
                              top=True,
                              right=True,
                              width=0.4,
                              direction='in',
                              length=2.0)
        plt.gca().minorticks_on()
        plt.xticks(fontsize=_fontsize)
        plt.yticks(fontsize=_fontsize)
        plt.plot()

    def plot_data(self, x, y, x_min, x_max):
        plt.cla()
        self.set_plot_style()
        plt.plot(x, y, **self.config)
        plt.xlim(x_min, x_max)
        plt.draw()

    def close_plt(self):
        plt.close()
