from dataclasses import replace
from collections.abc import Callable
from sample_balancer import LB

from matplotlib import pyplot as plt


def simulate_and_build_report(
        number_of_queries: int,
        number_of_users: int,
        distribution_function: Callable,
        use_sticky: bool,
        distribution_parameters: tuple[float, float]
):
    load_balancer = replace(LB)

    queries = (
        load_balancer.random_query(number_of_users, use_sticky)
        for _ in range(number_of_queries)
    )

    distribution_func_query = distribution_parameters + (number_of_queries,)

    times = sorted(i for i in distribution_function(*distribution_func_query) if 0 <= i <= 86400)
    time_queries = list(zip(queries, times))
    load_balancer.dispatch_many(time_queries)

    v1_queries_times, v1_queries_waits = load_balancer.target_groups[0].get_response_waits()
    plt.title('V1 response waiting time')
    plt.xlim(0, 86400)
    plt.plot(v1_queries_times, v1_queries_waits)
    plt.show()

    max_queues = []
    v1_instances_history = load_balancer.target_groups[0].get_queue_sizes()
    for batch in range(len(v1_instances_history) // 10 + 1):
        plt.figure(figsize=(10, 20))
        for idx, (times, q_sizes) in enumerate(v1_instances_history[batch:batch+10]):
            plt.subplot(5, 2, idx + 1)
            max_queues.append(max(q_sizes))
            plt.plot(times, q_sizes, label=f'Server {batch * 10 + idx}')
            plt.legend()
        plt.show()

    v1_timeouts_times, v1_timeouts_number = load_balancer.target_groups[0].get_timeouts()
    plt.title('V1 timeouts number')
    plt.xlim(0, 86400)
    plt.plot(v1_timeouts_times, v1_timeouts_number)
    plt.show()

    v2_queries_times, v2_queries_waits = load_balancer.target_groups[1].get_response_waits()
    plt.title('V2 response waiting time')
    plt.xlim(0, 86400)
    plt.plot(v2_queries_times, v2_queries_waits)
    plt.show()

    v2_instances_history = load_balancer.target_groups[1].get_queue_sizes()
    for batch in range(len(v2_instances_history) // 10 + 1):
        plt.figure(figsize=(10, 20))
        for idx, (times, q_sizes) in enumerate(v2_instances_history[batch:batch + 10]):
            plt.subplot(5, 2, idx + 1)
            max_queues.append(max(q_sizes))
            plt.plot(times, q_sizes, label=f'Server {batch * 10 + idx}')
            plt.legend()
        plt.show()

    v2_timeouts_times, v2_timeouts_number = load_balancer.target_groups[1].get_timeouts()
    plt.title('V2 timeouts number')
    plt.xlim(0, 86400)
    plt.plot(v2_timeouts_times, v2_timeouts_number)
    plt.show()

    queries_waits = v1_queries_waits + v2_queries_waits
    num_timeouts = len(v2_timeouts_times) - 2 + len(v1_timeouts_times) - 2

    print("Total timeouts:", num_timeouts)
    print("Success rate:", ((number_of_queries - num_timeouts) / number_of_queries) * 100)
    print("Mean-max queue:", sum(max_queues) / len(max_queues))
    print("Mean queries waits", sum(queries_waits) / len(queries_waits))

