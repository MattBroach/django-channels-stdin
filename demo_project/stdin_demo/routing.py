from channels.routing import ProtocolTypeRouter

from thoughts.consumers import ThoughtStdInConsumer


application = ProtocolTypeRouter({
    'stdin': ThoughtStdInConsumer,
})
