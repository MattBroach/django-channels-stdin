from channels.routing import ProtocolTypeRouter

from thoughts.consumers import ThoughtCLIConsumer


application = ProtocolTypeRouter({
    'cli': ThoughtCLIConsumer,
})
