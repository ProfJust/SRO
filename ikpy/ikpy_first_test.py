from ikpy.chain import Chain
from ikpy.link import OriginLink, URDFLink

arm = Chain(name='arm', links=[
    OriginLink(),
    URDFLink(
        name="joint1",
        origin_translation=[0, 0, 0],
        origin_orientation=[0, 0, 0],
        rotation=[0, 0, 1]
    ),
    URDFLink(
        name="joint2",
        origin_translation=[1, 0, 0],
        origin_orientation=[0, 0, 0],
        rotation=[0, 0, 1]
    )
])

target = [1, 1, 0]

angles = arm.inverse_kinematics(target)

print(angles)