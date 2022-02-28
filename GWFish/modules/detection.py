from scipy.interpolate import interp1d
import matplotlib.pyplot as plt
import numpy as np
import yaml

import GWFish.modules.constants as cst

class DetectorComponent:

    def __init__(self, name='ET', component='', Config='detConfig.yaml', plot=False):
        self.plot = plot
        self.id = component
        self.name = name + str(component)
        self.Config = Config
        self.setProperties()

    def setProperties(self):
        Config = self.Config
        k = self.id

        with open(Config) as f:
            doc = yaml.load(f, Loader=yaml.FullLoader)

        KeyC = []
        for key in doc.keys():
            KeyC.append(key)
        # print (KeyC)

        DD = str(self.name)
        # print (DD, "name of conf file: ", Config)

        if self.name[0:2] == 'ET':
            ETd = self.name[:-1]

            # print ("doing stuff for ET")
            self.lat = eval(doc[ETd]["lat"])
            self.lon = eval(doc[ETd]["lon"])
            self.opening_angle = eval(doc[ETd]["opening_angle"])
            self.arm_azimuth = eval(doc[ETd]["arm_azimuth"])

            self.e_long = np.array([-np.sin(self.lon), np.cos(self.lon), 0])
            self.e_lat = np.array(
                [-np.sin(self.lat) * np.cos(self.lon), -np.sin(self.lat) * np.sin(self.lon), np.cos(self.lat)])
            self.position = np.array(
                [np.cos(self.lat) * np.cos(self.lon), np.cos(self.lat) * np.sin(self.lon), np.sin(self.lat)])
            self.e1 = np.cos(self.arm_azimuth) * self.e_long + np.sin(self.arm_azimuth) * self.e_lat
            self.e2 = np.cos(self.arm_azimuth + self.opening_angle) * self.e_long + np.sin(
                self.arm_azimuth + self.opening_angle) * self.e_lat

            self.duty_factor = float(doc[ETd]["duty_factor"])
            self.plotrange = np.fromstring(doc[ETd]["plotrange"], dtype=float, sep=',')
            self.psd_data = np.loadtxt(str(doc[ETd]["psd_data"]))


        elif self.name[0:4] == 'LGWA':
            Detector = 'LGWA'
            doc_ = doc[Detector]
            for key in doc_.keys():
                doc__ = doc_[key]
                # for key in doc__.keys():
                # print (doc__)
                for i in range(4):
                    if (doc__["val"] == i):
                        self.lat = eval(doc__["lat"])
                        self.lon = eval(doc__["lon"])
                        self.hor_direction = eval(doc__["hor_direction"])
                        self.e_long = np.array([-np.sin(self.lon), np.cos(self.lon), 0])
                        self.e_lat = np.array(
                            [-np.sin(self.lat) * np.cos(self.lon), -np.sin(self.lat) * np.sin(self.lon),
                             np.cos(self.lat)])
                        self.e_rad = np.array([np.cos(self.lat) * np.cos(self.lon), np.cos(self.lat) * np.sin(self.lon),
                                               np.sin(self.lat)])
                        self.e1 = self.e_rad
                        self.e2 = np.cos(self.hor_direction) * self.e_long + np.sin(self.hor_direction) * self.e_lat
                        self.psd_data = np.loadtxt(str(doc__["psd_data"]))
                        self.duty_factor = float(doc__["duty_factor"])

                        # This block is for 2L detectors:
        elif DD in KeyC:

            Detector = str(self.name)
            # self.k = eval(doc[Detector]["k"])
            self.lat = eval(doc[Detector]["lat"])
            self.lon = eval(doc[Detector]["lon"])
            self.opening_angle = eval(doc[Detector]["opening_angle"])
            self.arm_azimuth = eval(doc[Detector]["arm_azimuth"])
            self.e_long = np.array([-np.sin(self.lon), np.cos(self.lon), 0])
            self.e_lat = np.array(
                [-np.sin(self.lat) * np.cos(self.lon), -np.sin(self.lat) * np.sin(self.lon), np.cos(self.lat)])
            self.position = np.array(
                [np.cos(self.lat) * np.cos(self.lon), np.cos(self.lat) * np.sin(self.lon), np.sin(self.lat)])
            self.e1 = np.cos(self.arm_azimuth) * self.e_long + np.sin(self.arm_azimuth) * self.e_lat
            self.e2 = np.cos(self.arm_azimuth + np.pi / 2.) * self.e_long + np.sin(
                self.arm_azimuth + np.pi / 2.) * self.e_lat
            self.duty_factor = float(doc[Detector]["duty_factor"])
            self.plotrange = np.fromstring(doc[Detector]["plotrange"], dtype=float, sep=',')
            self.psd_data = np.loadtxt(str(doc[Detector]["psd_data"]))
            print((self.lat), DD)

        else:
            print('Detector ' + self.name + ' invalid!')
            exit()

        self.Sn = interp1d(self.psd_data[:, 0], self.psd_data[:, 1], bounds_error=False, fill_value=1.)

        if self.plot:
            plt.figure()
            plt.loglog(self.psd_data[:, 0], np.sqrt(self.psd_data[:, 1]))
            plt.xlabel('Frequency [Hz]')
            plt.ylabel('Strain noise')
            plt.grid(True)
            plt.tight_layout()
            plt.savefig('Sensitivity_' + self.name + '.png')
            plt.close()

class Detector:

    def __init__(self, name='ET', number_of_signals=1, parameters=None, Config='detConfig.yaml', plot=False):
        self.components = []
        self.fisher_matrix = np.zeros((len(parameters), 9, 9))
        self.name = name
        self.Config = Config
        self.SNR = np.zeros(len(parameters))

        if name == 'LISA':
            self.location = 'solarorbit'
            self.mission_lifetime = 4 * 3.16e7

            fmin = 1e-3
            fmax = 0.3
            df = 1e-4

        elif name == 'LGWA':
            self.location = 'moon'
            self.mission_lifetime = 10 * 3.16e7

            fmin = 1e-3
            fmax = 4
            df = 1. / 4096.
        elif name == 'ET':
            self.location = 'earth'

            fmin = 2
            fmax = 1024
            df = 1. / 16.
        else:
            self.location = 'earth'

            fmin = 8
            fmax = 1024
            df = 1. / 4.

        self.frequencyvector = np.linspace(fmin, fmax, int((fmax - fmin) / df) + 1)
        self.frequencyvector = self.frequencyvector[:, np.newaxis]

        if name == 'ET' or name == 'LISA':
            for k in np.arange(3):
                self.components.append(DetectorComponent(name=name, component=k, Config=Config, plot=plot))
        elif name == 'LGWA':
            for k in np.arange(4):
                self.components.append(DetectorComponent(name=name, component=k, Config=Config, plot=plot))
        else:
            self.components.append(DetectorComponent(name=name, Config=Config, plot=plot))


class Network:

    def __init__(self, detector_ids = None, number_of_signals=1, detection_SNR=8., parameters=None, Config='detConfig.yaml',  plot=False):
        if detector_ids is None:
            detector_ids = ['ET']
        self.name = detector_ids[0]
        for id in detector_ids[1:]:
            self.name += '_' + id

        self.detection_SNR = detection_SNR
        self.SNR = np.zeros(len(parameters))
        self.Config=Config

        self.detectors = []
        for d in np.arange(len(detector_ids)):
            detectors = Detector(name=detector_ids[d], number_of_signals=number_of_signals, parameters=parameters, Config=Config, plot=plot)
            self.detectors.append(detectors)


def GreenwichMeanSiderealTime(gps):
    # calculate the Greenwhich mean sidereal time
    return np.mod(9.533088395981618 + (gps - 1126260000.) / 3600. * 24. / cst.sidereal_day, 24) * np.pi / 12.


def LunarMeanSiderealTime(gps):
    # calculate the Lunar mean sidereal time
    return np.mod((gps - 1126260000.) / (3600. * cst.lunar_sidereal_period), 1) * 2. * np.pi


def solarorbit(tt, R, eps, a0, b0):
    w0 = np.sqrt(cst.G * cst.Msol / R ** 3)  # w0 has a 1% error when using this equation for Earth orbit

    a = w0 * tt + a0
    b = b0 + 2 * np.pi / 3. * np.arange(3)
    pp = np.zeros((len(tt), 3, 3))
    # the trajectories describe th cartwheel motion, but not the breathing motion proportional to eps^2
    for k in np.arange(3):
        pp[:, k, :] = R * np.hstack((np.cos(a), np.sin(a), np.zeros_like(a))) \
                      + R * eps * np.hstack((0.5 * np.cos(2 * a - b[k]) - 1.5 * np.cos(b[k]),
                                             0.5 * np.sin(2 * a - b[k]) - 1.5 * np.sin(b[k]),
                                             -np.sqrt(3) * np.cos(a - b[k])))

    return pp


def yGW(i, j, polarizations, eij, theta, ra, psi, L, ff):
    ek = -np.array([np.sin(theta) * np.cos(ra), np.sin(theta) * np.sin(ra), np.cos(theta)])
    u = np.array([np.cos(theta) * np.cos(ra), np.cos(theta) * np.sin(ra), -np.sin(theta)])
    v = np.array([-np.sin(ra), np.cos(ra), 0])

    m = -u * np.sin(psi) - v * np.cos(psi)
    n = -u * np.cos(psi) + v * np.sin(psi)

    hxx = polarizations[:, 0] * (m[0] * m[0] - n[0] * n[0]) + polarizations[:, 1] * (m[0] * n[0] + n[0] * m[0])
    hxy = polarizations[:, 0] * (m[0] * m[1] - n[0] * n[1]) + polarizations[:, 1] * (m[0] * n[1] + n[0] * m[1])
    hxz = polarizations[:, 0] * (m[0] * m[2] - n[0] * n[2]) + polarizations[:, 1] * (m[0] * n[2] + n[0] * m[2])
    hyy = polarizations[:, 0] * (m[1] * m[1] - n[1] * n[1]) + polarizations[:, 1] * (m[1] * n[1] + n[1] * m[1])
    hyz = polarizations[:, 0] * (m[1] * m[2] - n[1] * n[2]) + polarizations[:, 1] * (m[1] * n[2] + n[1] * m[2])
    hzz = polarizations[:, 0] * (m[2] * m[2] - n[2] * n[2]) + polarizations[:, 1] * (m[2] * n[2] + n[2] * m[2])

    if i == np.mod(j + 1, 3):
        sgn = -1
    else:
        sgn = 1
    k = np.delete(np.array([0, 1, 2]), [i, j])[0]

    muk = (eij[:, np.mod(k + 1, 3), :] - eij[:, np.mod(k - 1, 3), :]) @ ek
    muk = muk[:, np.newaxis]
    muj = (eij[:, np.mod(j + 1, 3), :] - eij[:, np.mod(j - 1, 3), :]) @ ek
    muj = muj[:, np.newaxis]

    proj = eij[:, i, :] @ ek

    h_ifo = 0.5 * (eij[:, i, 0] ** 2 * hxx + eij[:, i, 1] ** 2 * hyy + eij[:, i, 2] ** 2 * hzz) \
            + eij[:, i, 0] * eij[:, i, 1] * hxy + eij[:, i, 0] * eij[:, i, 2] * hxz + eij[:, i, 1] * eij[:, i, 2] * hyz

    y = 0.5 / (1 + sgn * proj[:, np.newaxis]) * (
            np.exp(2j * np.pi * ff * L / c * (muk / 3. + 1.)) - np.exp(2j * np.pi * ff * L / cst.c * muj / 3.)) * h_ifo[:,np.newaxis]

    return y


def alpha(i, yGWij, L, ff):
    dL = np.exp(2j * np.pi * ff[:, 0] * L / cst.c)
    dL2 = np.exp(4j * np.pi * ff[:, 0] * L / cst.c)

    return yGWij[:, np.mod(i + 1, 3), i] - yGWij[:, np.mod(i - 1, 3), i] \
           + dL * (yGWij[:, i, np.mod(i - 1, 3)] - yGWij[:, i, np.mod(i + 1, 3)]) \
           + dL2 * (yGWij[:, np.mod(i - 1, 3), np.mod(i + 1, 3)] - yGWij[:, np.mod(i + 1, 3), np.mod(i - 1, 3)])


def AET(polarizations, eij, theta, ra, psi, L, ff):
    yGWij = np.zeros((len(ff), 3, 3), dtype='complex')
    for k1 in np.arange(3):
        for k2 in np.arange(k1 + 1, 3):
            yGWij[:, k1, k2] = yGW(k1, k2, polarizations, eij, theta, ra, psi, L, ff)[:, 0]
            yGWij[:, k2, k1] = yGW(k2, k1, polarizations, eij, theta, ra, psi, L, ff)[:, 0]

    a0 = alpha(0, yGWij, L, ff)
    a1 = alpha(1, yGWij, L, ff)
    a2 = alpha(2, yGWij, L, ff)

    A = (a2 - a0) / np.sqrt(2)
    E = (a0 - 2 * a1 + a2) / np.sqrt(6)
    T = (a0 + a1 + a2) / np.sqrt(3)

    return np.hstack((A[:, np.newaxis], E[:, np.newaxis], T[:, np.newaxis]))


def projection(parameters, detector, polarizations, timevector, max_time_until_merger):
    # rudimentary:
    # coords = SkyCoord(ra=ra, dec=dec, frame='icrs', unit='rad')
    # angles = coords.transform_to('barycentricmeanecliptic')

    if detector.location == 'earth':
        proj = projection_earth(parameters, detector, polarizations, timevector)
    elif detector.location == 'moon':
        proj = projection_moon(parameters, detector, polarizations, timevector, max_time_until_merger)
    elif detector.location == 'solarorbit':
        proj = projection_solarborbit(parameters, detector, polarizations, timevector, max_time_until_merger)
    else:
        print('Unknown detector location')
        exit(0)

    return proj

def projection_solarorbit(parameters, detector, polarizations, timevector):
    nt = len(polarizations[:, 0])
    ff = detector.frequencyvector

    components = detector.components

    if timevector.ndim == 1:
        timevector = timevector[:, np.newaxis]

    # note that RA/DEC are not translated into solar-centered coordinates! TO BE FIXED
    ra = parameters['ra']
    dec = parameters['dec']
    psi = parameters['psi']

    theta = np.pi / 2. - dec

    pp = solarorbit(timevector, cst.AU, components[0].eps, 0., 0.)
    eij = (pp[:, [1, 2, 0], :] - pp[:, [2, 0, 1], :]) / components[0].L

    # start_time = time.time()
    doppler_to_strain = cst.c / (components[0].L * 2 * np.pi * ff)
    proj = doppler_to_strain * AET(polarizations, eij, theta, ra, psi, components[0].L, ff)
    # print("Calculation of projection: %s seconds" % (time.time() - start_time))

    # define LISA observation window
    max_observation_time = detector.mission_lifetime
    tc = parameters['geocent_time']
    proj[np.where(timevector < tc - max_time_until_merger), :] = 0.j
    proj[np.where(timevector > tc - max_time_until_merger + max_observation_time), :] = 0.j

    i0 = np.argmin(np.abs(timevector - (tc - max_time_until_merger)))
    i1 = np.argmin(np.abs(timevector - (tc - max_time_until_merger + max_observation_time)))

    if 'id' in parameters:
        print('{} observed between {:.3f}Hz to {:.3f}Hz'.format(parameters['id'], ff[i0, 0], ff[i1, 0]))

    return proj

def projection_earth(parameters, detector, polarizations, timevector):
    """
    See Nishizawa et al. (2009) arXiv:0903.0528 for definitions of the polarisation tensors.
    [u, v, w] represent the Earth-frame
    [m, n, omega] represent the wave-frame
    Note1: there is a typo in the definition of the wave-frame in Nishizawa et al.
    Note2: it is computationally more expensive to use numpy.einsum instead of working with several vector quantities
    """

    # timevector = parameters['geocent_time'] * np.ones_like(timevector)  # switch off Earth's rotation

    nt = len(polarizations[:, 0])
    ff = detector.frequencyvector

    components = detector.components
    proj = np.zeros((nt, len(components)), dtype=complex)

    if timevector.ndim == 1:
        timevector = timevector[:, np.newaxis]

    ra = parameters['ra']
    dec = parameters['dec']
    psi = parameters['psi']

    theta = np.pi / 2. - dec
    gmst = GreenwichMeanSiderealTime(timevector)
    phi = ra - gmst

    # wave vector components
    kx = -np.sin(theta) * np.cos(phi)
    ky = -np.sin(theta) * np.sin(phi)
    kz = -np.cos(theta)

    # start_time = time.time()
    # u = np.array([np.cos(theta) * np.cos(phi[:,0]), np.cos(theta) * np.sin(phi[:,0]), -np.sin(theta)*np.ones_like(phi[:,0])])
    ux = np.cos(theta) * np.cos(phi[:, 0])
    uy = np.cos(theta) * np.sin(phi[:, 0])
    uz = -np.sin(theta)
    # v = np.array([-np.sin(phi[:,0]), np.cos(phi[:,0]), np.zeros_like(phi[:,0])])
    vx = -np.sin(phi[:, 0])
    vy = np.cos(phi[:, 0])
    vz = 0
    # print("Creating vectors u,v: %s seconds" % (time.time() - start_time))

    # start_time = time.time()
    # m = -u * np.sin(psi) - v * np.cos(psi)
    mx = -ux * np.sin(psi) - vx * np.cos(psi)
    my = -uy * np.sin(psi) - vy * np.cos(psi)
    mz = -uz * np.sin(psi) - vz * np.cos(psi)
    # n = -u * np.cos(psi) + v * np.sin(psi)
    nx = -ux * np.cos(psi) + vx * np.sin(psi)
    ny = -uy * np.cos(psi) + vy * np.sin(psi)
    nz = -uz * np.cos(psi) + vz * np.sin(psi)
    # print("Creating vectors m, n: %s seconds" % (time.time() - start_time))

    # start_time = time.time()
    # hpij = np.einsum('ij,kj->jik', m, m) - np.einsum('ij,kj->jik', n, n)
    # hcij = np.einsum('ij,kj->jik', m, n) + np.einsum('ij,kj->jik', n, m)
    # hij = np.einsum('i,ijk->ijk', polarizations[:, 0], hpij) + np.einsum('i,ijk->ijk', polarizations[:, 1], hcij)
    hxx = polarizations[:, 0] * (mx * mx - nx * nx) + polarizations[:, 1] * (mx * nx + nx * mx)
    hxy = polarizations[:, 0] * (mx * my - nx * ny) + polarizations[:, 1] * (mx * ny + nx * my)
    hxz = polarizations[:, 0] * (mx * mz - nx * nz) + polarizations[:, 1] * (mx * nz + nx * mz)
    hyy = polarizations[:, 0] * (my * my - ny * ny) + polarizations[:, 1] * (my * ny + ny * my)
    hyz = polarizations[:, 0] * (my * mz - ny * nz) + polarizations[:, 1] * (my * nz + ny * mz)
    hzz = polarizations[:, 0] * (mz * mz - nz * nz) + polarizations[:, 1] * (mz * nz + nz * mz)
    # print("Calculation GW tensor: %s seconds" % (time.time() - start_time))

    # start_time = time.time()
    for k in np.arange(len(components)):
        e1 = components[k].e1
        e2 = components[k].e2

        # interferometer position
        x_det = components[k].position[0] * cst.R_earth
        y_det = components[k].position[1] * cst.R_earth
        z_det = components[k].position[2] * cst.R_earth
        phase_shift = np.squeeze(x_det * kx + y_det * ky + z_det * kz) * 2 * np.pi / cst.c * np.squeeze(ff)

        # proj[:, k] = 0.5*(np.einsum('i,jik,k->j', e1, hij, e1) - np.einsum('i,jik,k->j', e2, hij, e2))
        proj[:, k] = 0.5 * (e1[0] ** 2 - e2[0] ** 2) * hxx \
                     + 0.5 * (e1[1] ** 2 - e2[1] ** 2) * hyy \
                     + 0.5 * (e1[2] ** 2 - e2[2] ** 2) * hzz \
                     + (e1[0] * e1[1] - e2[0] * e2[1]) * hxy \
                     + (e1[0] * e1[2] - e2[0] * e2[2]) * hxz \
                     + (e1[1] * e1[2] - e2[1] * e2[2]) * hyz
        proj[:, k] *= np.exp(-1.j * phase_shift)
    # print("Calculation of projection: %s seconds" % (time.time() - start_time))

    return proj


def projection_moon(parameters, detector, polarizations, timevector, max_time_until_merger):
    """
    See Nishizawa et al. (2009) arXiv:0903.0528 for definitions of the polarisation tensors.
    [u, v, w] represent the Earth-frame
    [m, n, omega] represent the wave-frame
    Note1: there is a typo in the definition of the wave-frame in Nishizawa et al.
    Note2: it is computationally more expensive to use numpy.einsum instead of working with several vector quantities
    """

    # timevector = parameters['geocent_time'] * np.ones_like(timevector)  # switch off Earth's rotation

    nt = len(polarizations[:, 0])

    components = detector.components
    proj = np.zeros((nt, len(components)), dtype=complex)

    if timevector.ndim == 1:
        timevector = timevector[:, np.newaxis]

    # note that RA/DEC are not translated into lunar-centered coordinates! TO BE FIXED
    ra = parameters['ra']
    dec = parameters['dec']
    psi = parameters['psi']

    theta = np.pi / 2. - dec
    lmst = LunarMeanSiderealTime(timevector)
    phi = ra - lmst

    # saving timevector and lmst for plotting
    # np.save('timevector.npy', timevector)
    # np.save('lmst.npy', lmst)

    # start_time = time.time()
    # u = np.array([np.cos(theta) * np.cos(phi[:,0]), np.cos(theta) * np.sin(phi[:,0]), -np.sin(theta)*np.ones_like(phi[:,0])])
    ux = np.cos(theta) * np.cos(phi[:, 0])
    uy = np.cos(theta) * np.sin(phi[:, 0])
    uz = -np.sin(theta)
    # v = np.array([-np.sin(phi[:,0]), np.cos(phi[:,0]), np.zeros_like(phi[:,0])])
    vx = -np.sin(phi[:, 0])
    vy = np.cos(phi[:, 0])
    vz = 0
    # print("Creating vectors u,v: %s seconds" % (time.time() - start_time))

    # start_time = time.time()
    # m = -u * np.sin(psi) - v * np.cos(psi)
    mx = -ux * np.sin(psi) - vx * np.cos(psi)
    my = -uy * np.sin(psi) - vy * np.cos(psi)
    mz = -uz * np.sin(psi) - vz * np.cos(psi)
    # n = -u * np.cos(psi) + v * np.sin(psi)
    nx = -ux * np.cos(psi) + vx * np.sin(psi)
    ny = -uy * np.cos(psi) + vy * np.sin(psi)
    nz = -uz * np.cos(psi) + vz * np.sin(psi)
    # print("Creating vectors m, n: %s seconds" % (time.time() - start_time))

    # start_time = time.time()
    # hpij = np.einsum('ij,kj->jik', m, m) - np.einsum('ij,kj->jik', n, n)
    # hcij = np.einsum('ij,kj->jik', m, n) + np.einsum('ij,kj->jik', n, m)
    # hij = np.einsum('i,ijk->ijk', polarizations[:, 0], hpij) + np.einsum('i,ijk->ijk', polarizations[:, 1], hcij)
    hxx = polarizations[:, 0] * (mx * mx - nx * nx) + polarizations[:, 1] * (mx * nx + nx * mx)
    hxy = polarizations[:, 0] * (mx * my - nx * ny) + polarizations[:, 1] * (mx * ny + nx * my)
    hxz = polarizations[:, 0] * (mx * mz - nx * nz) + polarizations[:, 1] * (mx * nz + nx * mz)
    hyy = polarizations[:, 0] * (my * my - ny * ny) + polarizations[:, 1] * (my * ny + ny * my)
    hyz = polarizations[:, 0] * (my * mz - ny * nz) + polarizations[:, 1] * (my * nz + ny * mz)
    hzz = polarizations[:, 0] * (mz * mz - nz * nz) + polarizations[:, 1] * (mz * nz + nz * mz)
    # print("Calculation GW tensor: %s seconds" % (time.time() - start_time))

    # start_time = time.time()
    for k in np.arange(len(components)):
        e1 = components[k].e1
        e2 = components[k].e2
        # proj[:, k] = np.einsum('i,jik,k->j', e1, hij, e2)
        proj[:, k] = e1[0] * e2[0] * hxx \
                     + e1[1] * e2[1] * hyy \
                     + e1[2] * e2[2] * hzz \
                     + (e1[0] * e2[1] + e2[0] * e1[1]) * hxy \
                     + (e1[0] * e2[2] + e2[0] * e1[2]) * hxz \
                     + (e1[1] * e2[2] + e2[1] * e1[2]) * hyz
    # print("Calculation of projection: %s seconds" % (time.time() - start_time))

    max_observation_time = detector.mission_lifetime
    tc = parameters['geocent_time']
    proj[np.where(timevector < tc - max_observation_time), :] = 0.j

    return proj


def lisaGWresponse(detector):
    ff = detector.frequencyvector
    nf = len(ff)

    polarizations = np.ones((nf, 2))
    timevector = np.zeros((nf, 1))

    components = detector.components

    ra = 0
    dec = np.pi / 2.
    psi = 0

    theta = np.pi / 2. - dec

    pp = solarorbit(timevector, cst.AU, components[0].eps, 0., 0.)
    eij = (pp[:, [1, 2, 0], :] - pp[:, [2, 0, 1], :]) / components[0].L

    doppler_to_strain = cst.c / (components[0].L * 2 * np.pi * ff)
    proj = doppler_to_strain * AET(polarizations, eij, theta, ra, psi, components[0].L, ff)

    plt.figure()
    plt.loglog(ff, np.abs(proj[:, 0]))
    plt.loglog(ff, np.abs(proj[:, 1]))
    plt.loglog(ff, np.abs(proj[:, 2]))
    plt.xlabel('Frequency [Hz]')
    plt.ylabel('GW response')
    plt.xlim((ff[0], ff[-1]))
    plt.ylim((1e-5, 10))
    plt.grid(True)
    plt.legend(['A', 'E', 'T'])
    plt.tight_layout()
    plt.savefig('ResponseGW_' + detector.name + '.png')
    plt.close()

    N = 10000
    for k in range(N):
        ra = 2 * np.pi * np.random.rand()
        costheta = 2 * np.random.rand() - 1
        psi = 2 * np.pi * np.random.rand()

        pp = solarorbit(timevector, cst.AU, components[0].eps, 0., 0.)
        eij = (pp[:, [1, 2, 0], :] - pp[:, [2, 0, 1], :]) / components[0].L

        doppler_to_strain = cst.c / (components[0].L * 2 * np.pi * ff)
        proj += (doppler_to_strain * AET(polarizations, eij, np.arccos(costheta), ra, psi, components[0].L,
                                         ff)) ** 2

    proj /= N

    psds = np.zeros((nf, 3))
    for k in range(3):
        psds[:, k] = components[k].Sn(ff[:, 0])

    plt.figure()
    plt.loglog(ff, np.sqrt(psds[:, 0] / np.abs(proj[:, 0])))
    plt.loglog(ff, np.sqrt(psds[:, 1] / np.abs(proj[:, 1])))
    plt.loglog(ff, np.sqrt(psds[:, 2] / np.abs(proj[:, 2])))
    plt.loglog(ff, 1 / np.sqrt(
        np.abs(proj[:, 0]) / psds[:, 0] + np.abs(proj[:, 1]) / psds[:, 1] + np.abs(proj[:, 2]) / psds[:, 2]))
    plt.xlabel('Frequency [Hz]')
    plt.ylabel('Sensitivity [Hz^{-1/2}]')
    plt.xlim((ff[0], ff[-1]))
    # plt.ylim((1e-5, 10))
    plt.grid(True)
    plt.legend(['A', 'E', 'T', 'combined'])
    plt.tight_layout()
    plt.savefig('Sensitivity_Skyav_GW_' + detector.name + '.png')
    plt.close()


def SNR(detector, signals, duty_cycle=False, plot=None):
    if signals.ndim == 1:
        signals = signals[:, np.newaxis]

    ff = detector.frequencyvector
    df = ff[1, 0] - ff[0, 0]
    components = detector.components

    SNRs = np.zeros(len(components))
    for k in np.arange(len(components)):

        SNRs[k] = np.sqrt(4 * df * np.sum(np.abs(signals[:, k]) ** 2 / components[k].Sn(ff[:, 0]), axis=0))
        #print(components[k].name + ': ' + str(SNRs[k]))
        if plot != None:
            plotrange = components[k].plotrange
            plt.figure()
            plt.loglog(ff, 2 * np.sqrt(np.abs(signals[:, k]) ** 2 * df))
            plt.loglog(ff, np.sqrt(components[k].Sn(ff)))
            plt.xlabel('Frequency [Hz]')
            plt.ylabel('Strain spectra')
            plt.xlim((plotrange[0], plotrange[1]))
            plt.ylim((plotrange[2], plotrange[3]))
            plt.grid(True)
            plt.tight_layout()
            #plt.savefig('SignalNoise_' + str(components[k].name) + '_' + plot + '.png')
            plt.savefig('SignalNoise_' + str(components[k].name) + '.png')
            plt.close()

            plt.figure()
            plt.semilogx(ff, 2 * np.sqrt(np.abs(signals[:, k]) ** 2 / components[k].Sn(ff[:, 0]) * df))
            plt.xlabel('Frequency [Hz]')
            plt.ylabel('SNR spectrum')
            plt.xlim((plotrange[0], plotrange[1]))
            plt.grid(True)
            plt.tight_layout()
            #plt.savefig('SNR_density_' + str(components[k].name) + '_' + plot + '.png')
            plt.savefig('SNR_density_' + str(components[k].name) + '.png')
            plt.close()

        # set SNRs to zero if interferometer is not operating (according to its duty factor [0,1])
        if duty_cycle:
            operating = np.random.rand()
            #print('operating = ',operating)
            if components[k].duty_factor < operating:
                SNRs[k] = 0.

    return SNRs


def analyzeDetections(network, parameters, population, networks_ids):
    param_names = ['ra', 'dec', 'psi', 'iota', 'luminosity_distance', 'mass_1', 'mass_2', 'geocent_time', 'phase']

    detSNR = network.detection_SNR

    ns = len(network.SNR)
    N = len(networks_ids)

    param_pick = param_names + ['redshift']
    save_data = parameters[param_pick]
    if 'id' in parameters.columns:
        save_data = np.c_[parameters['id'], save_data]

    for n in np.arange(N):
        maxz = 0

        network_ids = networks_ids[n]
        network_name = '_'.join([network.detectors[k].name for k in network_ids])

        print('Network: ' + network_name)

        SNR = 0
        for d in network_ids:
            SNR += network.detectors[d].SNR ** 2
        SNR = np.sqrt(SNR)

        save_data = np.c_[save_data, SNR]

        threshold = SNR > detSNR[1]

        ndet = len(np.where(threshold)[0])

        if ndet > 0:
            maxz = np.max(parameters['redshift'].iloc[np.where(threshold)].to_numpy())
        print(
            'Detected signals with SNR>{:.3f}: {:.3f} ({:} out of {:}); z<{:.3f}'.format(detSNR[1], ndet / ns, ndet, ns,
                                                                                         maxz))

        print('SNR: {:.3f} (min) , {:.3f} (max) '.format(np.min(SNR), np.max(SNR)))

    if 'id' in parameters.columns:
        np.savetxt('Signals_' + population + '.txt', save_data, delimiter=' ', fmt='%s '+"%.3f "*(len(save_data[0,:])-1))
    else:
        np.savetxt('Signals_' + population + '.txt', save_data, delimiter=' ', fmt='%.3f')
