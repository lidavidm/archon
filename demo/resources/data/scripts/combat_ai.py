def basic_ai(output, context, performAttacks, enemy, player):
    weapons = []
    for slot in ('left hand', 'right hand'):
        if enemy.attributes.equip.get(slot):
            weapons.append(enemy.attributes.equip[slot])
    if weapons:
        output.display("Attack!")
        performAttacks(output, context, enemy, player, 'physical', *weapons)
    else:
        output.display("The enemy does nothing.")
