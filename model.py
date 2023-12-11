import dataclasses
import random
from dataclasses import dataclass
from collections.abc import Callable
from typing import Any
from enum import Enum
from queue import PriorityQueue


class QueryMethod(Enum):
    get = 'GET'
    post = 'POST'


@dataclass
class Query:
    path: str
    method: QueryMethod
    session_key: str
    use_sticky: bool = False


@dataclass
class DistributionConfig:
    distribution_func: Callable
    args: list[Any]

    def sample(self):
        return self.distribution_func(*self.args)[0]


@dataclass
class PathHandlerConfig:
    path: str
    method: QueryMethod
    time_distribution: DistributionConfig

    def dispatch(self) -> float:
        return self.time_distribution.sample()


# idle_time_precentage, mean waits, mean in-system, number_of_queries, mean_queue_size
@dataclass
class ServerConfig:
    path_handlers: list[PathHandlerConfig]
    not_exist_process_time: float
    break_time_distr: DistributionConfig
    init_time_distr: DistributionConfig
    state: str = 'healthy'
    _queue_changes: PriorityQueue = dataclasses.field(default_factory=PriorityQueue)
    _release_time: float = 0

    def __post_init__(self):
        paths_and_methods = [(handler.path, handler.method) for handler in self.path_handlers]
        if len(set(paths_and_methods)) != len(paths_and_methods):
            raise ValueError("Paths and methods should be a unique combination")

    def dispatch(self, query: Query, current_time: float) -> tuple[float, float]:
        time_to_process = self.not_exist_process_time
        for handler in self.path_handlers:
            if handler.path == query.path and handler.method == query.method:
                time_to_process = handler.dispatch()
                break
        request_time_processing_start = max(current_time, self._release_time)
        self._release_time = request_time_processing_start + time_to_process
        self._queue_changes.put((current_time, 'added'))
        self._queue_changes.put((self._release_time, 'removed'))
        return self._release_time - current_time, time_to_process

    def get_queue_history(self) -> tuple[list[float], list[float]]:
        cur_size = 0
        q_length = []
        times = []
        while not self._queue_changes.empty():
            time, event_name = self._queue_changes.get()
            times.append(time)
            if event_name == 'added':
                cur_size += 1
            else:
                cur_size -= 1
            q_length.append(cur_size)
        return times, q_length

@dataclass
class TargetGroup:
    path_pattern: str
    server_config: ServerConfig
    number_of_instances: int
    health_check_path: str
    health_check_method: QueryMethod
    health_check_interval: int
    timeout: int
    _events: PriorityQueue = dataclasses.field(default_factory=PriorityQueue)
    _ptr: int = 0
    _servers: dict[int, ServerConfig] = dataclasses.field(default_factory=dict)
    _response_waits: list[tuple[float, float]] = dataclasses.field(default_factory=list)
    _processing_waits: list[float] = dataclasses.field(default_factory=list)
    _sticky_mapper: dict[str, int] = dataclasses.field(default_factory=dict)
    _instances_history: list[ServerConfig] = dataclasses.field(default_factory=list)
    _timeouts: list[float] = dataclasses.field(default_factory=list)
    _health_check_max_time: float = 0

    def __post_init__(self):
        self._servers = {i: ServerConfig(
            path_handlers=self.server_config.path_handlers,
            not_exist_process_time=self.server_config.not_exist_process_time,
            break_time_distr=self.server_config.break_time_distr,
            init_time_distr=self.server_config.init_time_distr
        ) for i in range(self.number_of_instances)}
        for server in self._servers.values():
            self._instances_history.append(server)
        max_time = 0
        for idx, server in self._servers.items():
            break_time = server.break_time_distr.sample()
            max_time = max(max_time, break_time)
            self._events.put((break_time, idx, 'break'))
        check_time = self.health_check_interval
        while check_time <= max_time:
            self._health_check_max_time = check_time
            for idx in self._servers:
                self._events.put((check_time, idx, 'health_check'))
            check_time += self.health_check_interval

    def put_event(self, time: float, body, event_type: str):
        try:
            self._events.put((time, body, event_type))
        except TypeError:
            self._events.put((time + 0.01, body, event_type))
        check_time = self._health_check_max_time
        while check_time <= time:
            self._health_check_max_time = check_time
            for idx in self._servers:
                self._events.put((check_time, idx, 'health_check'))
            check_time += self.health_check_interval

    def handle(self, time: float, body, event_type: str):
        if event_type == 'health_check':
            idx = body
            if self._servers[idx].state != 'init':
                query = Query(self.health_check_path, self.health_check_method, '')
                release_time, time_to_process = self._servers[idx].dispatch(query, time)

                if release_time >= self.timeout:
                    self.put_event(time + self.timeout, idx, 'make_unhealthy')
                    return
                self.put_event(release_time + time, (idx, time), 'health_check_response')
        elif event_type == 'health_check_response':
            idx, submit_time = body
            if self._servers[idx].state == 'broken':
                self.put_event(submit_time + self.timeout, idx, 'make_unhealthy')
                return
        elif event_type == 'make_unhealthy':
            idx = body
            new_server = ServerConfig(
                path_handlers=self.server_config.path_handlers,
                not_exist_process_time=self.server_config.not_exist_process_time,
                break_time_distr=self.server_config.break_time_distr,
                init_time_distr=self.server_config.init_time_distr
            )
            self._servers[idx] = new_server
            init_time = self._servers[idx].init_time_distr.sample()
            start_time = time + init_time
            self._instances_history.append(new_server)
            new_server.state = 'init'
            self.put_event(start_time, idx, 'init_finish')
        elif event_type == 'break':
            idx = body
            self._servers[idx].state = 'broken'
        elif event_type == 'init_finish':
            idx = body
            self._servers[idx].state = 'healthy'
        elif event_type == 'query':
            query = body
            for i in range(self.number_of_instances):
                if self._servers[self._ptr].state != 'init':
                    break
                self._ptr = (self._ptr + 1) % len(self._servers)

            ptr = self._ptr
            if not query.use_sticky:
                self._ptr = (self._ptr + 1) % len(self._servers)
            else:
                if query.session_key not in self._sticky_mapper:
                    self._sticky_mapper[query.session_key] = self._ptr
                    self._ptr = (self._ptr + 1) % len(self._servers)
                ptr = self._sticky_mapper[query.session_key]
            response_wait, processing_wait = self._servers[ptr].dispatch(query, time)
            if self._servers[ptr].state != 'healthy' or response_wait > self.timeout:
                self.put_event(time + self.timeout, ptr, 'query_fail')
                self._response_waits.append((time, self.timeout))
                self._processing_waits.append(self.timeout)
            else:
                self.put_event(
                    time + response_wait,
                    (ptr, response_wait),
                    'query_response'
                )
                self._response_waits.append((time, response_wait))
                self._processing_waits.append(processing_wait)
        elif event_type == 'query_response':
            idx, response_wait = body
            if self._servers[idx].state == 'healthy':
                return True
            if self._servers[idx].state != 'healthy':
                self.put_event(time - response_wait + self.timeout, idx, 'query_fail')
        elif event_type == 'query_fail':
            self._timeouts.append(time)

    def dispatch_many(self, queries: list[tuple[Query, float]]):
        max_t = 0
        for query, time in queries:
            max_t = max(max_t, time)
            self.put_event(time, query, 'query')

        while self._events.qsize():
            t, q, e = self._events.get()
            if t > max_t + self.timeout:
                break
            self.handle(t, q, e)

    def get_response_waits(self) -> tuple[list[float], list[float]]:
        times = []
        waits = []
        for time, wait in sorted(self._response_waits):
            times.append(time)
            waits.append(wait)
        return times, waits

    def get_queue_sizes(self) -> list[tuple[list[float], list[float]]]:
        return [server.get_queue_history() for server in self._instances_history]

    def get_timeouts(self) -> tuple[list[float], list[float]]:
        values = [i for i in range(len(self._timeouts) + 1)]
        return [0] + self._timeouts + [86400], values + [len(self._timeouts)]


@dataclass
class LoadBalancer:
    target_groups: list[TargetGroup]
    _timeouts: list[float] = dataclasses.field(default_factory=list)

    def dispatch_many(self, queries: list[tuple[Query, float]]):
        queries_for_tg: list[list[tuple[Query, float]]] = [[] for _ in range(len(self.target_groups))]
        for query, time in queries:
            for idx, tg in enumerate(self.target_groups):
                if query.path.startswith(tg.path_pattern):
                    queries_for_tg[idx].append((query, time))
                    break
        for idx, tg in enumerate(self.target_groups):
            tg.dispatch_many(queries_for_tg[idx])

    def random_query(self, max_sessions: int, use_sticky: bool) -> Query:
        path_handlers = []
        for tg in self.target_groups:
            for path_handler in tg.server_config.path_handlers:
                path_handlers.append(path_handler)
        path_handler = random.choice(path_handlers[:-1])
        session = str(random.randint(0, max_sessions))
        return Query(
            path=path_handler.path,
            method=path_handler.method,
            session_key=session,
            use_sticky=use_sticky
        )
