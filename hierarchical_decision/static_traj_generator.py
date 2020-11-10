#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# =====================================
# @Time    : 2020/10/12
# @Author  : Yang Guan; Yangang Ren (Tsinghua Univ.)
# @FileName: hierarchical_decision.py
# =====================================
from dynamics_and_models import ReferencePath
import numpy as np
from math import pi, sqrt, sin, cos
import bezier

L, W = 4.8, 2.0
LANE_WIDTH = 3.75
LANE_NUMBER = 3
CROSSROAD_SIZE = 50
control_ext = 15


class StaticTrajectoryGenerator(object):
    def __init__(self, task, state, mode, v_light=0):
        # state: [v_x, v_y, r, x, y, phi(°)]
        self.mode = mode
        self.path_num = 3  # the number of static trajectories
        self.exp_v = 8.
        self.N = 25
        self.order = [0 for _ in range(self.path_num)]
        self.task = task
        self.ego_info_dim = 6
        self.feature_points_all = self._future_points_init(self.task)
        self.state = state[:self.ego_info_dim]
        self.ref_index = np.random.choice(list(range(self.path_num)))
        self._future_point_choice(self.state)
        self.construct_ref_path(self.task, self.state, v_light)

    def generate_traj(self, task, state, v_light=0):
        """"generate two reference trajectory in real time"""
        if self.mode == 'static_traj':
            self.path_list = []
            for path_index in range(self.path_num):
                ref = ReferencePath(self.task)
                ref.set_path(self.mode, path_index)
                self.path_list.append(ref)
        else:
            self._future_point_choice(state)
            self.construct_ref_path(task, state, v_light)
        return self.path_list, self.feature_points

    def _future_points_init(self, task):
        feature_points = []
        meter_pointnum_ratio = 30
        if task == 'left':
            end_offsets = [LANE_WIDTH * 0.5, LANE_WIDTH * 1.5, LANE_WIDTH * 2.5]
            start_offsets = [LANE_WIDTH * 0.5]

            # for start_offset in start_offsets:
            #     for end_offset in end_offsets:
            #         control_point1 = start_offset, -CROSSROAD_SIZE/2,               0.5 * pi
            #         control_point2 = start_offset, -CROSSROAD_SIZE/2 + control_ext, 0.5 * pi
            #         control_point3 = -CROSSROAD_SIZE/2 + control_ext, end_offset,   -pi
            #         control_point4 = -CROSSROAD_SIZE/2, end_offset,                 -pi
            #         control_point5 = -CROSSROAD_SIZE, end_offset,                   -pi
            #
            #         node = [control_point1, control_point2, control_point3, control_point4, control_point5]
            #         feature_points.append(node)

            for start_offset in start_offsets:
                for end_offset in end_offsets:
                    control_point1 = start_offset, -CROSSROAD_SIZE/2,               0.5 * pi
                    control_point2 = -CROSSROAD_SIZE/2, end_offset,                 -pi
                    control_point3 = -CROSSROAD_SIZE/2 - control_ext, end_offset,   -pi
                    control_point4 = -CROSSROAD_SIZE, end_offset,                   -pi

                    node = [control_point1, control_point2, control_point3, control_point4]
                    feature_points.append(node)

        elif task == 'right':
            raise SystemExit('unfinished for right turn tasks!')

        elif task == 'straight':
            raise SystemExit('unfinished for right go straight tasks!')

        return feature_points

    def _future_point_choice(self, state):
        # choose the forward feature points according to the current state
        self.feature_points = []
        x, y, v, phi = state[3], state[4], state[0], state[5] / 180 * pi
        for i, item in enumerate(self.feature_points_all):
            if -CROSSROAD_SIZE/2 <= y:
                if x > -CROSSROAD_SIZE/2:
                    self.feature_points.append(list(item[1:]))
                elif -CROSSROAD_SIZE/2 - control_ext < x <= -CROSSROAD_SIZE/2:
                    self.feature_points.append(list(item[2:]))
                else:
                    self.feature_points.append(list(item[3:]))
            else:
                self.feature_points = self._future_points_init(self.task)

        # calculate the init flag and L0, L3
        self.flag = np.ones([self.path_num])
        self.dist_bound = 2. * np.ones([self.path_num])
        self.L0 = 2. * np.ones([self.path_num])
        self.L3 = 5. * np.ones([self.path_num])

        # 首先根据当前的state和feature_point的距离计算L0
        for path_index in range(0, self.path_num):
            feature_point = self.feature_points[path_index][0]
            dist = sqrt((x - feature_point[0])**2 + (y - feature_point[1])**2)
            if dist < self.dist_bound[path_index]:
                self.feature_points[path_index] = self.feature_points[path_index][1:]
                print('Updating feature point…')

    def construct_ref_path(self, task, state, v_light):
        x, y, v, phi = state[3], state[4], state[0], state[5] / 180 * pi
        state = [x, y, v, phi]

        # todo:随机选择轨迹
        self.ref_index = 1
        if self.ref_index == 0:
            self.new_point_bound = [0.16, 0.06]
        else:
            self.new_point_bound = [0.06, 0.16]

        self.path_list = []

        for path_index in range(0, self.path_num, 1):
            if v_light != 0 and y < -18 and task != 'right':         # red or yellow light
                feature_point = self.feature_points[path_index][self.order[path_index]]
                dist = sqrt((x - feature_point[0]) ** 2 + (y - feature_point[1]) ** 2)         # dist between vehicle and stopline
                if dist < 3.0:
                    planed_trj = np.array([[state[0], state[1], state[2], state[3] * 180 / pi]])
                    planed_trj = np.repeat(planed_trj, 21, axis=0)
                    current_path = planed_trj[:, 0], planed_trj[:, 1], planed_trj[:, 3]
                    self.path_list.append(ReferencePath(self.task, self.mode, current_path))
                else:
                    self.L0[path_index] = sqrt((x - feature_point[0]) ** 2 + (y - feature_point[1]) ** 2) / 2.0
                    self.L3[path_index] = sqrt((x - feature_point[0]) ** 2 + (y - feature_point[1]) ** 2) / 4.0
                    X0 = x; X1 = x + self.L0[path_index] * cos(phi); X2 = feature_point[0] - self.L3[path_index] * cos(feature_point[3]); X3 = feature_point[0];
                    Y0 = y; Y1 = y + self.L0[path_index] * sin(phi); Y2 = feature_point[1] - self.L3[path_index] * sin(feature_point[3]); Y3 = feature_point[1];
                    t = np.linspace(0, 1, self.N + 1, endpoint=True)
                    X_t = X0 * (1 - t) ** 3 + 3 * X1 * t * (1 - t) ** 2 + 3 * X2 * t ** 2 * (1 - t) + X3 * t ** 3
                    Y_t = Y0 * (1 - t) ** 3 + 3 * Y1 * t * (1 - t) ** 2 + 3 * Y2 * t ** 2 * (1 - t) + Y3 * t ** 3
                    xs_1, ys_1 = X_t[:-1], Y_t[:-1]
                    xs_2, ys_2 = X_t[1:],  Y_t[1:]
                    v = self.exp_v * np.ones(len(X_t))
                    phis_1 = np.arctan2(ys_2 - ys_1, xs_2 - xs_1) * 180 / pi
                    phis_1 = np.append(phis_1, feature_point[3] * 180 /pi)

                    planed_traj = X_t, Y_t, phis_1
                    self.path_list.append(ReferencePath(self.task, self.mode, planed_traj))

            else:                                                    # green light
                # if self.flag[path_index] == 0:
                #     print('Updating feature points')
                #     self.order[path_index] += 1
                #     feature_point = self.feature_points[path_index][self.order[path_index]]
                #     self.L0[path_index] = sqrt((x - feature_point[0])**2 + (y - feature_point[1])**2) / 2.0
                #     self.L3[path_index] = sqrt((x - feature_point[0])**2 + (y - feature_point[1])**2) / 4.0

                feature_point1, feature_point2 = self.feature_points[path_index][0], self.feature_points[path_index][1]
                planed_trj = self.trajectory_planning(state, feature_point1, feature_point2, self.L0[path_index], self.L3[path_index])
                ref = ReferencePath(self.task)
                ref.set_path(self.mode, path_index=path_index, path=planed_trj)
                self.path_list.append(ref)

        self.path = self.path_list[self.ref_index].path

    def trajectory_planning(self, state, point1, point2, L0, L3):
        X0 = state[0]; X1 = state[0] + L0 * cos(state[3]); X2 = point1[0] - L3 * cos(point1[2]); X3 = point1[0]
        Y0 = state[1]; Y1 = state[1] + L0 * sin(state[3]); Y2 = point1[1] - L3 * sin(point1[2]); Y3 = point1[1]

        node = np.asfortranarray([[X0, X1, X2, X3], [Y0, Y1, Y2, Y3]], dtype=np.float32)
        curve = bezier.Curve(node, degree=3)
        # s_vals = np.linspace(0, 1.0, int(pi / 2 * (CROSSROAD_SIZE / 2 + LANE_WIDTH / 2)) * 30)
        s_vals = np.linspace(0, 1.0, 500)
        trj_data = curve.evaluate_multi(s_vals)
        trj_data = trj_data.astype(np.float32)
        xs_1, ys_1 = trj_data[0, :-1], trj_data[1, :-1]
        xs_2, ys_2 = trj_data[0, 1:], trj_data[1, 1:]
        phis_1 = np.arctan2(ys_2 - ys_1, xs_2 - xs_1) * 180 / pi
        planed_trj = xs_1, ys_1, phis_1

        return planed_trj

    # def trajectory_planning(self, x0, x_des1, x_des2, L0, L3, new_method_bound, v=4.0, T=0.1, N=20):
    #     traj, L0, L3, flag = self.reference_trajectory(x0, x_des1, x_des2, L0, L3, v, T, N, new_method_bound)
    #     return traj, L0, L3, flag
    #
    # def reference_trajectory(self, x0, x_des1, x_des2, L0, L3, v, T, N, NEW_PATH_BOUND, RELATIVE_ERR=0.02):
    #     # used for tracking!
    #     # only some of state info is necessary, e.g. x and y locations!
    #     traj = np.zeros([N + 1, len(x0)])
    #     traj_t = np.zeros(N + 1)
    #     ErrorBound = []
    #
    #     X0 = x0[0]; X1 = x0[0] + L0 * cos(x0[3]); X2 = x_des1[0] - L3 * cos(x_des1[3]); X3 = x_des1[0]; X4 = x_des2[0];
    #     Y0 = x0[1]; Y1 = x0[1] + L0 * sin(x0[3]); Y2 = x_des1[1] - L3 * sin(x_des1[3]); Y3 = x_des1[1]; Y4 = x_des2[1];
    #
    #     phi_3 = x_des1[-1]
    #     phi_4 = x_des2[-1]
    #     traj[0, :] = x0[0], x0[1], x0[2], x0[3] * 180 /pi
    #
    #     tt0 = 0
    #
    #     for i in range(N):
    #         delta_L = v * T
    #         ErrorBound.append(RELATIVE_ERR * delta_L)
    #         tt = max(2 * delta_L, 1)  # 前提：t=1对应的弧长>1!
    #         delta_tt = tt / 2.
    #         X_temp, Y_temp = self.bezier_generator(X0, X1, X2, X3, X4, Y0, Y1, Y2, Y3, Y4, phi_3, phi_4, tt0 + tt)
    #
    #         distance = ((X_temp - traj[i, 0]) ** 2 + (Y_temp - traj[i, 1]) ** 2) ** 0.5
    #
    #         while abs(distance - delta_L) > ErrorBound[i]:  # binary search!
    #             if distance - delta_L > 0:
    #                 tt = tt - delta_tt
    #             else:
    #                 tt = tt + delta_tt
    #             delta_tt = delta_tt / 2.
    #             X_temp, Y_temp = self.bezier_generator(X0, X1, X2, X3, X4, Y0, Y1, Y2, Y3, Y4, phi_3, phi_4, tt0 + tt)
    #             distance = ((X_temp - traj[i, 0]) ** 2 + (Y_temp - traj[i, 1]) ** 2) ** 0.5
    #
    #         traj_t[i + 1] = tt0 + tt
    #         traj[i + 1, 0] = X_temp
    #         traj[i + 1, 1] = Y_temp
    #
    #         tt0 = tt0 + tt
    #
    #     t1 = traj_t[1]  # t1: relative position of current state on last trajectory!
    #
    #     if t1 >= NEW_PATH_BOUND:
    #         flag = 0
    #         L0 = 0
    #         L3 = 0
    #     else:
    #         tau1 = t1 + 0.5 * (1 - t1)
    #         tau2 = t1 + 1. / 3. * (1 - t1)
    #         # A_tempx = np.array([ [3./8., 3./8.], [4./9., 2./9.] ])
    #         b_tempx = np.array([
    #             X0 * (1 - tau1) ** 3 + 3 * X1 * tau1 * (1 - tau1) ** 2 + 3 * X2 * tau1 ** 2 * (1 - tau1) + X3 * tau1 ** 3 -
    #             traj[1, 0] / 8. - X3 / 8.,
    #             X0 * (1 - tau2) ** 3 + 3 * X1 * tau2 * (1 - tau2) ** 2 + 3 * X2 * tau2 ** 2 * (1 - tau2) + X3 * tau2 ** 3 -
    #             traj[1, 0] / 27. * 8. - X3 / 27.
    #         ])
    #         # X_new = np.dot(np.linalg.inv(A_tempx),b_tempx)得到的向量第一个元素为新的X1，第二个元素为新的X2
    #         X_new = np.dot(np.array([[-2.667, 4.5], [5.333, -4.5]]), b_tempx)
    #
    #         # A_tempy = np.array([ [3./8., 3./8.], [4./9., 2./9.] ])
    #         b_tempy = np.array([
    #             Y0 * (1 - tau1) ** 3 + 3 * Y1 * tau1 * (1 - tau1) ** 2 + 3 * Y2 * tau1 ** 2 * (1 - tau1) + Y3 * tau1 ** 3 -
    #             traj[1, 1] / 8. - Y3 / 8.,
    #             Y0 * (1 - tau2) ** 3 + 3 * Y1 * tau2 * (1 - tau2) ** 2 + 3 * Y2 * tau2 ** 2 * (1 - tau2) + Y3 * tau2 ** 3 -
    #             traj[1, 1] / 27. * 8. - Y3 / 27.
    #         ])
    #         # Y_new = np.dot(np.linalg.inv(A_tempy),b_tempy)#得到的向量第一个元素为新的X1，第二个元素为新的X2
    #         Y_new = np.dot(np.array([[-2.667, 4.5], [5.333, -4.5]]), b_tempy)
    #         # print('Y_new[0] = ',Y_new[0])
    #
    #         L0 = ((X_new[0] - traj[1, 0]) ** 2 + (Y_new[0] - traj[1, 1]) ** 2) ** 0.5
    #         L3 = ((X_new[1] - X3) ** 2 + (Y_new[1] - Y3) ** 2) ** 0.5
    #         flag = 1
    #     return traj, L0, L3, flag
    #
    # def bezier_generator(self, X0, X1, X2, X3, X4, Y0, Y1, Y2, Y3, Y4, phi_3, phi_4, t):
    #     # X0,Y0: current point
    #     # X1,Y1,X2,Y2: auxiliary point
    #     # X3,Y3: next feature point
    #     # X4,Y4: nextnext feature point
    #     HYPERPARA_BEZIER_1 = 2.0
    #     HYPERPARA_BEZIER_2 = 4.0
    #
    #     if t < 1:
    #         X_t = X0 * (1 - t) ** 3 + 3 * X1 * t * (1 - t) ** 2 + 3 * X2 * t ** 2 * (1 - t) + X3 * t ** 3
    #         Y_t = Y0 * (1 - t) ** 3 + 3 * Y1 * t * (1 - t) ** 2 + 3 * Y2 * t ** 2 * (1 - t) + Y3 * t ** 3
    #     else:  # 先判断下一段是直线还是1/4圆弧
    #         if phi_3 == phi_4 and (X3 == X4 or Y3 == Y4):  # 下一段全局路径是直线
    #             X_t = X3 + (t - 1) * cos(phi_3)
    #             Y_t = Y3 + (t - 1) * sin(phi_3)
    #         else:
    #             L0 = ((X3 - X4) ** 2 + (Y3 - Y4) ** 2) ** 0.5 / HYPERPARA_BEZIER_1
    #             L3 = ((X3 - X4) ** 2 + (Y3 - Y4) ** 2) ** 0.5 / HYPERPARA_BEZIER_2
    #             X3_0 = X3 + L0 * cos(phi_3);
    #             X3_1 = X4 - L3 * cos(phi_4)
    #             Y3_0 = Y3 + L0 * sin(phi_3);
    #             Y3_1 = Y4 - L3 * sin(phi_4)
    #             X_t = X3 * (2 - t) ** 3 + 3 * X3_0 * (t - 1) * (2 - t) ** 2 + 3 * X3_1 * (t - 1) ** 2 * (2 - t) + X4 * (
    #                         t - 1) ** 3
    #             Y_t = Y3 * (2 - t) ** 3 + 3 * Y3_0 * (t - 1) * (2 - t) ** 2 + 3 * Y3_1 * (t - 1) ** 2 * (2 - t) + Y4 * (
    #                         t - 1) ** 3
    #     return X_t, Y_t

