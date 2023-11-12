import numpy as np
from script import (
    LoadBalancer, TargetGroup, ServerConfig, QueryMethod, PathHandlerConfig,
    DistributionConfig, Query
)

LB = LoadBalancer(
    target_groups=[
        TargetGroup(
            path_pattern='v1/',
            server_config=ServerConfig(
                path_handlers=[PathHandlerConfig(
                    path='v1/users',
                    method=QueryMethod.get,
                    time_distribution=DistributionConfig(
                        distribution_func=np.random.normal,
                        args=[3, 0.1, 1]
                    ),
                ), PathHandlerConfig(
                    path='v1/users',
                    method=QueryMethod.post,
                    time_distribution=DistributionConfig(
                        distribution_func=np.random.normal,
                        args=[7, 0.2, 1]
                    ),
                ), PathHandlerConfig(
                    path='v1/auth',
                    method=QueryMethod.post,
                    time_distribution=DistributionConfig(
                        distribution_func=np.random.normal,
                        args=[2, 0.05, 1]
                    ),
                ), PathHandlerConfig(
                    path='v1/report',
                    method=QueryMethod.get,
                    time_distribution=DistributionConfig(
                        distribution_func=np.random.normal,
                        args=[20, 5, 1]
                    ),
                )],
                not_exist_process_time=3,
                break_time_distr=DistributionConfig(
                    distribution_func=np.random.normal,
                    args=[100, 10, 1]
                ),
                init_time_distr=DistributionConfig(
                    distribution_func=np.random.normal,
                    args=[100, 10, 1]
                ),
            ),
            number_of_instances=6,
            health_check_path='v1/users',
            health_check_method=QueryMethod.get,
            health_check_interval=30,
            timeout=60
        ),
        TargetGroup(
            path_pattern='v2/',
            server_config=ServerConfig(
                path_handlers=[PathHandlerConfig(
                    path='v2/users',
                    method=QueryMethod.get,
                    time_distribution=DistributionConfig(
                        distribution_func=np.random.normal,
                        args=[2, 0.1, 1]
                    ),
                ), PathHandlerConfig(
                    path='v2/users',
                    method=QueryMethod.post,
                    time_distribution=DistributionConfig(
                        distribution_func=np.random.normal,
                        args=[5, 0.2, 1]
                    ),
                ), PathHandlerConfig(
                    path='v2/auth',
                    method=QueryMethod.post,
                    time_distribution=DistributionConfig(
                        distribution_func=np.random.normal,
                        args=[10, 0.05, 1]
                    ),
                ), PathHandlerConfig(
                    path='v2/report',
                    method=QueryMethod.get,
                    time_distribution=DistributionConfig(
                        distribution_func=np.random.normal,
                        args=[25, 5, 1]
                    ),
                )],
                not_exist_process_time=3,
                break_time_distr=DistributionConfig(
                    distribution_func=np.random.normal,
                    args=[100, 10, 1]
                ),
                init_time_distr=DistributionConfig(
                    distribution_func=np.random.normal,
                    args=[100, 10, 1]
                ),
            ),
            number_of_instances=2,
            health_check_path='v2/users',
            health_check_method=QueryMethod.get,
            health_check_interval=30,
            timeout=60
        )
    ]
)


if __name__ == '__main__':
    LB.dispatch(Query(method=QueryMethod.get, path='v2/users', session_key='1'), 11.3)
    LB.dispatch(Query(method=QueryMethod.post, path='v1/auth', session_key='2'), 25.24)
    LB.dispatch(Query(method=QueryMethod.get, path='v2/report', session_key='1'), 30.1)