#!/usr/bin/python
import argparse
import logging
import sys

from subprocess import check_output, CalledProcessError


def print_values():
    configs = []
    configs.extend([
        current_config('/main/capturesettings/f-number/'),
        current_config('/main/capturesettings/shutterspeed/'),
        current_config('/main/imgsettings/iso/'),
        current_config('/main/capturesettings/expprogram/'),
        current_config('/main/capturesettings/capturemode/'),
        current_config('/main/capturesettings/exposuremetermode/'),
        current_config('/main/capturesettings/focusmetermode/'),
        current_config('/main/capturesettings/exposurecompensation/'),
    ])
    logging.info('Current Values:')
    for config in configs:
        logging.info('\t{}: {}'.format(*reversed(config)))


def current_config(param):
    try:
        config = check_output(['gphoto2', '--get-config', param]).split('\n')
    except CalledProcessError:
        logging.error('Camera Error... Exiting')
        sys.exit(0)
        return

    current = filter(lambda x: 'Current' in x, config)[0].split(': ')[1]
    label = filter(lambda x: 'Label' in x, config)[0].split(': ')[1]
    return current, label


def calculate_compensations(shots, evstep):
    param = '/main/capturesettings/exposurecompensation/'
    exposures = check_output(['gphoto2', '--get-config', param]).split('\n')
    EVs = map(
        lambda x: int(x.split()[2]),
        filter(lambda x: 'Choice: ' in x, exposures))
    valid_steps = EVs[len(EVs)/2 + 1:]
    total_steps = len(EVs) - 1
    min_step = (EVs[-1] - EVs[0])/total_steps
    if evstep not in valid_steps:
        logging.error('Exposure step not valid. Must be one of {}'.format(
            [int(s) for s in valid_steps]))
        sys.exit(0)

    step = int(round(evstep/min_step))
    idxs = [comp*step for comp in range(
        (shots+1)/2) if comp*step <= total_steps/2]
    valid_idxs = [-i + len(EVs)/2 for i in idxs]
    if 0 in idxs:
        valid_idxs.extend([i + len(EVs)/2 for i in idxs[1:]])
    else:
        valid_idxs.extend([i + len(EVs)/2 for i in idxs])
    if len(valid_idxs) < shots:
        logging.error(
            '{} out of exposure compensations discarded'.format(
                shots-len(valid_idxs)))
    compensations = [EVs[i] for i in valid_idxs]
    info = '{} brackets will be taken with the following compensations {}'
    logging.debug(info.format(len(
        compensations), [c/1000.0 for c in compensations]))
    return compensations


def take_hdr(compensations):
    cmds = ['/usr/bin/gphoto2']
    cmds.append('--quiet')
    cmds.extend(['--set-config', '/main/settings/capturetarget=1'])
    for comp in compensations:
        cmds.extend([
            '--set-config-value',
            '/main/capturesettings/exposurecompensation={}'.format(comp),
        ])
        cmds.append('--capture-image')
    cmds.extend(['--set-config',
                 '/main/capturesettings/exposurecompensation=0'])
    check_output(cmds)

if __name__ == '__main__':
    # Parse command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('-e', '--evstep',
                        metavar='N', type=int, default=1000,
                        help='Exposure compensation on each step.')
    parser.add_argument('-s', '--shots',
                        metavar='N', type=int, default=3,
                        help='Number of shots.')
    parser.add_argument('-d', '--debug', action='store_true',
                        help='DEBUG Mode.')
    args = parser.parse_args()

    # Logging configuration
    logging_level = logging.DEBUG if args.debug else logging.INFO
    if args.debug:
        logging.basicConfig(
            level=logging_level,
            format='%(asctime)s %(levelname)s: %(message)s.'
        )
    logging.getLogger('pydslr').setLevel(logging_level)
    print_values()
    comps = calculate_compensations(args.shots, args.evstep)
    take_hdr(comps)
