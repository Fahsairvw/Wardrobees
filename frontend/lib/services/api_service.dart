import 'package:http/http.dart' as http;
import 'dart:convert';
import 'dart:io' show Platform;
import '../models/wardrobe.dart';
import '../models/cloth_item.dart';

class ApiService {
  // Change this to your backend URL
  // For Android emulator: http://10.0.2.2:8000
  // For iOS simulator: http://localhost:8000
  // For physical device: http://<your_machine_ip>:8000
  // For Web: http://127.0.0.1:8000 (if localhost doesn't work)
  static const String baseUrl = 'http://127.0.0.1:8000';

  // Health check
  static Future<bool> healthCheck() async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/'),
      ).timeout(const Duration(seconds: 5));

      return response.statusCode == 200;
    } catch (e) {
      print('Health check error: $e');
      return false;
    }
  }

  // Get wardrobe with all items
  static Future<Wardrobe> getWardrobe(int userId) async {
    try {
      final url = '$baseUrl/wardrobe/$userId';
      print('DEBUG: Fetching wardrobe from $url');
      
      final response = await http.get(
        Uri.parse(url),
      ).timeout(const Duration(seconds: 10));

      print('DEBUG: Response status: ${response.statusCode}');
      
      if (response.statusCode == 200) {
        final wardrobe = Wardrobe.fromJson(jsonDecode(response.body));
        print('DEBUG: Got ${wardrobe.items.length} items');
        return wardrobe;
      } else {
        throw Exception('Failed to load wardrobe: ${response.statusCode}');
      }
    } catch (e) {
      print('DEBUG: Error fetching wardrobe: $e');
      throw Exception('Error fetching wardrobe: $e');
    }
  }

  // Get wardrobe stats
  static Future<Map<String, dynamic>> getWardrobeStats(int userId) async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/wardrobe/$userId/stats'),
      ).timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        return jsonDecode(response.body);
      } else {
        throw Exception('Failed to load stats: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Error fetching stats: $e');
    }
  }

  // Get single item
  static Future<ClothItem> getItem(int itemId) async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/items/$itemId'),
      ).timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        return ClothItem.fromJson(jsonDecode(response.body));
      } else {
        throw Exception('Failed to load item: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Error fetching item: $e');
    }
  }

  // Delete item
  static Future<bool> deleteItem(int itemId) async {
    try {
      final response = await http.delete(
        Uri.parse('$baseUrl/items/$itemId'),
      ).timeout(const Duration(seconds: 10));

      return response.statusCode == 200;
    } catch (e) {
      throw Exception('Error deleting item: $e');
    }
  }

  // Log wear
  static Future<bool> logWear(int itemId) async {
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/items/$itemId/wear'),
      ).timeout(const Duration(seconds: 10));

      return response.statusCode == 200;
    } catch (e) {
      throw Exception('Error logging wear: $e');
    }
  }

  // Detect clothes from image
  static Future<Map<String, dynamic>> detectClothes(String imagePath) async {
    try {
      var request = http.MultipartRequest(
        'POST',
        Uri.parse('$baseUrl/detect'),
      );

      request.files.add(await http.MultipartFile.fromPath('file', imagePath));

      var response = await request.send().timeout(const Duration(seconds: 30));

      if (response.statusCode == 200) {
        final responseData = await response.stream.bytesToString();
        return jsonDecode(responseData);
      } else {
        throw Exception('Detection failed: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Error detecting clothes: $e');
    }
  }

  // Search items
  static Future<List<ClothItem>> searchItems(int wardrobeId, String query) async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/search')
            .replace(queryParameters: {'wardrobe_id': wardrobeId.toString(), 'query': query}),
      ).timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        final List<dynamic> data = jsonDecode(response.body);
        return data.map((item) => ClothItem.fromJson(item as Map<String, dynamic>)).toList();
      } else {
        throw Exception('Search failed: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Error searching items: $e');
    }
  }

  // Build image URL
  static String getImageUrl(String? imageUrl) {
    if (imageUrl == null || imageUrl.isEmpty) {
      return 'https://via.placeholder.com/150?text=No+Image';
    }
    if (imageUrl.startsWith('http')) {
      return imageUrl;
    }
    // If it's a relative path like '/storage/images/...', prepend base URL
    return '$baseUrl$imageUrl';
  }
}
