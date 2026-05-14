import 'cloth_item.dart';

class Wardrobe {
  final int wardrobeId;
  final int userId;
  final int total;
  final Map<String, List<ClothItem>> grouped;
  final List<ClothItem> items;

  Wardrobe({
    required this.wardrobeId,
    required this.userId,
    required this.total,
    required this.grouped,
    required this.items,
  });

  factory Wardrobe.fromJson(Map<String, dynamic> json) {
    final groupedData = <String, List<ClothItem>>{};
    
    if (json['grouped'] != null) {
      (json['grouped'] as Map<String, dynamic>).forEach((category, items) {
        groupedData[category] = (items as List)
            .map((item) => ClothItem.fromJson(item as Map<String, dynamic>))
            .toList();
      });
    }

    var itemsList = <ClothItem>[];
    if (json['items'] != null) {
      itemsList = (json['items'] as List)
          .map((item) => ClothItem.fromJson(item as Map<String, dynamic>))
          .toList();
    }

    return Wardrobe(
      wardrobeId: json['wardrobe_id'] ?? 0,
      userId: json['user_id'] ?? 0,
      total: json['total'] ?? 0,
      grouped: groupedData,
      items: itemsList,
    );
  }
}
