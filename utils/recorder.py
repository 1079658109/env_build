#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# =====================================
# @Time    : 2020/12/11
# @Author  : Yang Guan (Tsinghua Univ.)
# @FileName: recorder.py
# =====================================
import numpy as np
import seaborn as sns
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.pyplot as ticker
from matplotlib.pyplot import MultipleLocator
import math
sns.set(style="darkgrid")


class Recorder(object):
    def __init__(self):
        self.val2record = ['v_x', 'v_y', 'r', 'x', 'y', 'phi',
                           'steer', 'a_x', 'delta_y', 'delta_v', 'delta_phi',
                           'cal_time', 'ref_index', 'beta']

        self.comp2record = ['v_x', 'v_y', 'r', 'x', 'y', 'phi', 'adp_steer', 'adp_a_x', 'mpc_steer', 'mpc_a_x',
                            'delta_y', 'delta_v', 'delta_phi', 'adp_time', 'mpc_time', 'adp_ref', 'mpc_ref', 'beta']

        self.val2plot = ['v_x', 'r', 'steer', 'a_x', 'cal_time', 'ref_index', 'beta']
        self.key2label = dict(v_x='Velocity [m/s]',
                              r='Yaw rate [rad/s]',
                              steer='Steer angle [$\circ$]',
                              a_x='Acceleration [$\mathrm {m/s^2}$]',
                              cal_time='Computing time [ms]',
                              ref_index='Selected path',
                              beta='Side slip angle[$\circ$]')
        self.ego_info_dim = 6
        self.per_tracking_info_dim = 3
        self.num_future_data = 0
        self.data_across_all_episodes = []
        self.val_list_for_an_episode = []
        self.comp_list_for_an_episode = []
        self.comp_data_across_all_episodes = []

    def reset(self):
        self.data_across_all_episodes.append(self.val_list_for_an_episode)
        self.comp_data_across_all_episodes.append(self.comp_list_for_an_episode)
        self.val_list_for_an_episode = []
        self.comp_list_for_an_episode = []

    def record(self, obs, act, cal_time, ref_index):
        ego_info, tracking_info, _ = obs[:self.ego_info_dim], \
                                     obs[self.ego_info_dim:self.ego_info_dim + self.per_tracking_info_dim * (
                                               self.num_future_data + 1)], \
                                     obs[self.ego_info_dim + self.per_tracking_info_dim * (
                                               self.num_future_data + 1):]
        v_x, v_y, r, x, y, phi = ego_info
        delta_y, delta_phi, delta_v = tracking_info[:3]
        steer, a_x = act[0]*0.4, act[1]*3-1.

        # transformation
        beta = 0 if v_x == 0 else np.arctan(v_y/v_x) * 180 / math.pi
        steer = steer * 180 / math.pi
        self.val_list_for_an_episode.append(np.array([v_x, v_y, r, x, y, phi, steer, a_x, delta_y,
                                        delta_phi, delta_v, cal_time, ref_index, beta]))

    # For comparison of MPC and ADP
    def record_compare(self, obs, adp_act, mpc_act, adp_time, mpc_time, adp_ref, mpc_ref, mode='ADP'):
        ego_info, tracking_info, _ = obs[:self.ego_info_dim], \
                                     obs[self.ego_info_dim:self.ego_info_dim + self.per_tracking_info_dim * (
                                               self.num_future_data + 1)], \
                                     obs[self.ego_info_dim + self.per_tracking_info_dim * (
                                               self.num_future_data + 1):]
        v_x, v_y, r, x, y, phi = ego_info
        delta_y, delta_phi, delta_v = tracking_info[:3]
        adp_steer, adp_a_x = adp_act[0]*0.4, adp_act[1]*3-1.
        mpc_steer, mpc_a_x = mpc_act[0], mpc_act[1]

        # transformation
        beta = 0 if v_x == 0 else np.arctan(v_y/v_x) * 180 / math.pi
        adp_steer = adp_steer * 180 / math.pi
        mpc_steer = mpc_steer * 180 / math.pi
        self.comp_list_for_an_episode.append(np.array([v_x, v_y, r, x, y, phi, adp_steer, adp_a_x, mpc_steer, mpc_a_x,
                                            delta_y, delta_phi, delta_v, adp_time, mpc_time, adp_ref, mpc_ref, beta]))

    def save(self):
        np.save('./data_across_all_episodes.npy', np.array(self.data_across_all_episodes))
        np.save('./comp_data_across_all_episodes.npy', np.array(self.comp_data_across_all_episodes))

    def load(self):
        self.data_across_all_episodes = np.load('./comp_data_across_all_episodes.npy', allow_pickle=True)

    def plot_current_episode_curves(self):
        real_time = np.array([0.1 * i for i in range(len(self.val_list_for_an_episode))])
        all_data = [np.array([vals_in_a_timestep[index] for vals_in_a_timestep in self.val_list_for_an_episode])
                    for index in range(len(self.val2record))]
        data_dict = dict(zip(self.val2record, all_data))
        for key in data_dict.keys():
            if key in self.val2plot:
                f = plt.figure(key)
                ax = f.add_axes([0.20, 0.12, 0.78, 0.86])
                sns.lineplot(real_time, data_dict[key], linewidth=2, palette="bright")
                ax.set_ylabel(self.key2label[key], fontsize=15)
                ax.set_xlabel("Time [s]", fontsize=15)
                plt.yticks(fontsize=15)
                plt.xticks(fontsize=15)
        plt.show()

    def plot_ith_episode_curves(self, i):
        episode2plot = self.data_across_all_episodes[i]
        real_time = np.array([0.1*i for i in range(len(episode2plot))])
        all_data = [np.array([vals_in_a_timestep[index] for vals_in_a_timestep in episode2plot])
                    for index in range(len(self.comp2record))]
        data_dict = dict(zip(self.comp2record, all_data))
        color = ['cyan', 'indigo', 'magenta', 'coral', 'b', 'brown', 'c']
        i = 0
        for key in data_dict.keys():
            if key in self.val2plot:
                f = plt.figure(key)
                ax = f.add_axes([0.20, 0.12, 0.78, 0.86])
                if key == 'ref_index':
                    sns.lineplot(real_time, data_dict[key] + 1, linewidth=2, palette="bright", color=color[i])
                    plt.ylim([0.5, 3.5])
                    x_major_locator = MultipleLocator(10)
                    # ax.xaxis.set_major_locator(x_major_locator)
                    ax.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))

                elif key == 'v_x':
                    sns.lineplot(real_time, data_dict[key], linewidth=2, palette="bright", color=color[i])
                    plt.ylim([-0.5, 10.])
                elif key == 'cal_time':
                    sns.lineplot(real_time, data_dict[key] * 1000, linewidth=2, palette="bright", color=color[i])
                    plt.ylim([0, 3000])
                elif key == 'a_x':
                    sns.lineplot(real_time, np.clip(data_dict[key], -3.0, 1.5), linewidth=2, palette="bright", color=color[i])
                    # sns.lineplot(real_time, data_dict[key], linewidth=2, palette="bright", color=color[i])
                    plt.ylim([-4.0, 4.0])
                elif key == 'steer':
                    sns.lineplot(real_time, data_dict[key], linewidth=2, palette="bright", color=color[i])
                    plt.ylim([-25, 25])
                elif key == 'beta':
                    sns.lineplot(real_time, data_dict[key], linewidth=2, palette="bright", color=color[i])
                    plt.ylim([-15, 15])
                elif key == 'r':
                    sns.lineplot(real_time, data_dict[key], linewidth=2, palette="bright", color=color[i])
                    plt.ylim([-0.8, 0.8])
                else:
                    sns.lineplot(real_time, data_dict[key], linewidth=2, palette="bright", color=color[i])

                ax.set_ylabel(self.key2label[key], fontsize=15)
                ax.set_xlabel("Time [s]", fontsize=15)
                plt.yticks(fontsize=15)
                plt.xticks(fontsize=15)
                i += 1
        plt.show()

    def plot_mpc_rl(self, i):
        episode2plot = self.data_across_all_episodes[i] if i is not None else self.comp_list_for_an_episode
        real_time = np.array([0.1 * i for i in range(len(episode2plot))])
        all_data = [np.array([vals_in_a_timestep[index] for vals_in_a_timestep in episode2plot])
                    for index in range(len(self.comp2record))]
        data_dict = dict(zip(self.comp2record, all_data))

        df_mpc = pd.DataFrame({'algorithms': 'MPC',
                               'iteration': real_time,
                               'steer': data_dict['mpc_steer'],
                               'acc': data_dict['mpc_a_x'],
                               'time': data_dict['mpc_time'],
                               'ref_path': data_dict['mpc_ref'] + 1
                               })
        df_rl = pd.DataFrame({'algorithms': 'ADP',
                              'iteration': real_time,
                              'steer': data_dict['adp_steer'],
                              'acc': data_dict['adp_a_x'],
                              'time': data_dict['adp_time'],
                              'ref_path': data_dict['adp_ref'] + 1
                              })

        total_df = df_mpc.append([df_rl], ignore_index=True)
        f1 = plt.figure(1)
        ax1 = f1.add_axes([0.155, 0.12, 0.82, 0.86])
        sns.lineplot(x="iteration", y="steer", hue="algorithms", data=total_df, linewidth=2, palette="bright", )
        ax1.set_ylabel('Front wheel angle [$\circ$]', fontsize=15)
        ax1.set_xlabel("Time[s]", fontsize=15)
        ax1.legend(frameon=False, fontsize=15)
        plt.yticks(fontsize=15)
        plt.xticks(fontsize=15)

        f2 = plt.figure(2)
        ax2 = f2.add_axes([0.155, 0.12, 0.82, 0.86])
        sns.lineplot(x="iteration", y="acc", hue="algorithms", data=total_df, linewidth=2, palette="bright", )
        ax2.set_ylabel('Acceleration [$\mathrm {m/s^2}$]', fontsize=15)
        ax2.set_xlabel('Time[s]', fontsize=15)
        ax2.legend(frameon=False, fontsize=15)
        # plt.xlim(0, 3)
        # plt.ylim(-40, 80)
        plt.yticks(fontsize=15)
        plt.xticks(fontsize=15)

        f3 = plt.figure(3)
        ax3 = f3.add_axes([0.155, 0.12, 0.82, 0.86])
        sns.lineplot(x="iteration", y="time", hue="algorithms", data=total_df, linewidth=2, palette="bright", )
        plt.yscale('log')
        ax3.set_ylabel('Computing time [ms]', fontsize=15)
        ax3.set_xlabel("Time[s]", fontsize=15)
        handles, labels = ax3.get_legend_handles_labels()
        # ax3.legend(handles=handles[1:], labels=labels[1:], loc='upper left', frameon=False, fontsize=15)
        ax3.legend(handles=handles[:], labels=labels[:], frameon=False, fontsize=15)
        plt.yticks(fontsize=15)
        plt.xticks(fontsize=15)

        f4 = plt.figure(4)
        ax4 = f4.add_axes([0.155, 0.12, 0.82, 0.86])
        sns.lineplot(x="iteration", y="ref_path", hue="algorithms", data=total_df, dashes=True, linewidth=2, palette="bright", )
        ax4.lines[1].set_linestyle("--")
        ax4.set_ylabel('Selected path', fontsize=15)
        ax4.set_xlabel("Time[s]", fontsize=15)
        ax4.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
        ax4.legend(frameon=False, fontsize=15)
        # plt.xlim(0, 3)
        # plt.ylim(-40, 80)
        plt.yticks(fontsize=15)
        plt.xticks(fontsize=15)
        plt.show()






