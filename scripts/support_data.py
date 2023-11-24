ADMIN_IDEAS = [
    'innovativeness_ideas',
    'economic_ideas',
    'expansion_ideas',
    'administrative_ideas',
    'humanist_ideas',
    'judiciary',
    'development',
    'strong_men',
    # 'fem_boy', # Commented since the same as strong_men
    # 'public_admin',
    'centralism',
    'decentralism',
]
ADMIN_GOV_IDEAS = [   
    'monarchie0',
    'republik0',
    'aristo0',
    'diktatur0',
    'horde0',
]
ADMIN_RELIGION_IDEAS = [
    'religious_ideas',
    'katholisch0',
    'protestant0',
    'reformiert0',
    'orthodox0',
    'islam0',
    'tengri0',
    'hindu0',
    'confuci0',
    'budda0',
    'norse0',
    'shinto0',
    'cathar0',
    'coptic0',
    'romuva0',
    'suomi0',
    'jew0',
    'slav0',
    'helle0',
    'mane0',
    'animist0',
    'feti0',
    'zoro0',
    'ancli0',
    'nahu0',
    'mesoam0',
    'inti0',
    'tote0',
    'shia0',
    'ibadi0',
    'hussite0',
    'alche0'
]
ADMIN_NOT_COMPATIBLE = [
    ('strong_men', 'fem_boy',),
    ('centralism', 'decentralism',),
]
DIPLO_IDEAS = [
    'spy_ideas',
    'dynastic',
    'influence_ideas',
    'trade_ideas',
    'exploration_ideas',
    'maritime_ideas',
    'heavy_ship',
    'galley_ship',
    'trade_ship',
    'colonial_emp',
    'assimilation',
    'sociaty',
    'propaganda',
    'fleet_base',
    'nationalismus',
    'konigreich0',
    'imperialismus'
]
DIPLO_EMPIRE_IDEAS = [
    'konigreich0',
    'imperialismus'
]
DIPLO_NOT_COMPATIBLE = [
    ('konigreich0', 'imperialismus'),
    ('heavy_ship', 'galley_ship'),
    ('heavy_ship', 'trade_ship'),
    ('galley_ship', 'trade_ship')
]
MIL_IDEAS = [
    'offensive',
    'defensive',
    'quality',
    'quantity',
    'general_staff',
    'standing_army',
    'conscription',
    'merc_army',
    'weapon_quality',
    'fortress',
    'war_production',
    'formation0',
    'militarism',
    'shock_ideas',
    'fire_ideas'
 ]
MIL_NOT_COMPATIBLE = [
    ('offensive', 'defensive'),
    ('quality', 'quantity'),
    ('standing_army', 'conscription'),
    ('shock_ideas', 'fire_ideas')
]