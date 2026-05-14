class ClothItem {
  final int itemId;
  final int wardrobeId;
  final String category;
  final String? color;
  final String? imageUrl;
  final int wearCount;
  final String? name;
  final String? texture;
  final Map<String, dynamic>? careGuide;

  ClothItem({
    required this.itemId,
    required this.wardrobeId,
    required this.category,
    this.color,
    this.imageUrl,
    required this.wearCount,
    this.name,
    this.texture,
    this.careGuide,
  });

  factory ClothItem.fromJson(Map<String, dynamic> json) {
    return ClothItem(
      itemId: json['item_id'] ?? 0,
      wardrobeId: json['wardrobe_id'] ?? 0,
      category: json['category'] ?? 'other',
      color: json['color'],
      imageUrl: json['image_url'] ?? json['mask_url'],
      wearCount: json['wear_count'] ?? 0,
      name: json['name'],
      texture: json['texture'],
      careGuide: json['care_guide'],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'item_id': itemId,
      'wardrobe_id': wardrobeId,
      'category': category,
      'color': color,
      'image_url': imageUrl,
      'wear_count': wearCount,
      'name': name,
      'texture': texture,
      'care_guide': careGuide,
    };
  }
}
