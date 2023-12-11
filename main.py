from numpy import random

from report import simulate_and_build_report

if __name__ == '__main__':
    # simulate_and_build_report(
    #     10000,
    #     100,
    #     random.normal,
    #     False,
    #     (43200, 4000)
    # )
    # simulate_and_build_report(
    #     20000,
    #     100,
    #     random.normal,
    #     False,
    #     (43200, 4000)
    # )
    # simulate_and_build_report(
    #     20000,
    #     100,
    #     random.uniform,
    #     False,
    #     (0, 86400)
    # )
    # simulate_and_build_report(
    #     100000,
    #     100,
    #     random.uniform,
    #     False,
    #     (0, 86400)
    # )
    # simulate_and_build_report(
    #     10000,
    #     100,
    #     random.gamma,
    #     False,
    #     (200, 250)
    # )
    simulate_and_build_report(
        10000,
        100,
        random.normal,
        True,
        (43200, 4000)
    )
