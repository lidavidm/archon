#!/usr/bin/env python3


def main(output, context, player, npc, conversation):
    if 'shop' in npc.attributes:
        buyMult, sellMult, inventory = npc.attributes['shop']
        while True:
            choice = output.menu('  {key}. {description}', '  > ',
                                 'Invalid choice.',
                                 'Buy Item', 'Sell Item', 'Exit')
            if choice == 0:
                while True:
                    pass
            elif choice == 1:
                while True:
                    pass
            else:
                output.display("Goodbye.")
                return
    else:
        output.error("I'm afraid that I have nothing to sell.")
