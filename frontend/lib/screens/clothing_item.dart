import 'package:flutter/material.dart';
import '../models/cloth_item.dart';
import '../services/api_service.dart';

class ClothingItemScreen extends StatefulWidget {
  final ClothItem item;

  const ClothingItemScreen({
    super.key,
    required this.item,
  });

  @override
  State<ClothingItemScreen> createState() => _ClothingItemScreenState();
}

class _ClothingItemScreenState extends State<ClothingItemScreen> {
  bool _isDeleting = false;

  Future<void> _deleteItem() async {
    // Show confirmation dialog
    final shouldDelete = await showDialog<bool>(
      context: context,
      builder: (BuildContext context) {
        return AlertDialog(
          title: const Text('Delete Item'),
          content: const Text('Are you sure to delete this item? This action cannot be undone.'),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('Cancel'),
            ),
            TextButton(
              onPressed: () => Navigator.pop(context, true),
              child: const Text('Delete', style: TextStyle(color: Colors.red)),
            ),
          ],
        );
      },
    );

    if (shouldDelete != true) return;

    setState(() => _isDeleting = true);

    try {
      final success = await ApiService.deleteItem(widget.item.itemId);
      if (success) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Item deleted successfully')),
          );
          Navigator.pop(context, true); // Return true to indicate refresh needed
        }
      } else {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Failed to delete item')),
          );
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error deleting item: $e')),
        );
      }
    } finally {
      if (mounted) setState(() => _isDeleting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final imageUrl = ApiService.getImageUrl(widget.item.imageUrl);
    
    return Scaffold(
      backgroundColor: const Color(0xFFFFFDF7),
      appBar: AppBar(
        backgroundColor: const Color(0xFFFFFDF7),
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back, color: Colors.black),
          onPressed: () => Navigator.pop(context),
        ),
        title: Text(
          widget.item.name ?? widget.item.category,
          style: const TextStyle(
            color: Colors.black,
            fontSize: 20,
            fontFamily: 'Inter',
            fontWeight: FontWeight.w600,
          ),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.delete_outline, color: Colors.red),
            onPressed: _isDeleting ? null : _deleteItem,
            tooltip: 'Delete item',
          ),
        ],
      ),
      body: SingleChildScrollView(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Item Image
              Container(
                width: double.infinity,
                height: 367,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(20),
                  image: DecorationImage(
                    image: NetworkImage(imageUrl),
                    fit: BoxFit.cover,
                  ),
                ),
              ),
              const SizedBox(height: 28),

              // Category & Color Info
              Text(
                widget.item.category.toUpperCase(),
                style: const TextStyle(
                  color: Colors.grey,
                  fontSize: 12,
                  fontFamily: 'Inter',
                  fontWeight: FontWeight.w500,
                  letterSpacing: 1.0,
                ),
              ),
              const SizedBox(height: 8),
              if (widget.item.color != null)
                Text(
                  'Color: ${widget.item.color}',
                  style: const TextStyle(
                    color: Colors.black,
                    fontSize: 16,
                    fontFamily: 'Inter',
                    fontWeight: FontWeight.w500,
                  ),
                ),
              if (widget.item.texture != null)
                Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: Text(
                    'Texture: ${widget.item.texture}',
                    style: const TextStyle(
                      color: Colors.black,
                      fontSize: 16,
                      fontFamily: 'Inter',
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ),
              const SizedBox(height: 24),

              // Usage Section
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(16),
                decoration: ShapeDecoration(
                  color: const Color(0xFFFFF0F5),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(20),
                  ),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'Usage',
                      style: TextStyle(
                        color: Colors.black,
                        fontSize: 18,
                        fontFamily: 'Inter',
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: 12),
                    Text(
                      '${widget.item.wearCount} times',
                      style: const TextStyle(
                        color: Colors.black,
                        fontSize: 16,
                        fontFamily: 'Inter',
                        fontWeight: FontWeight.w400,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),

              // Care Guidance Section
              if (widget.item.careGuide != null)
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(16),
                  decoration: ShapeDecoration(
                    color: const Color(0xFFFFF0F5),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(20),
                    ),
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Care Guidance',
                        style: TextStyle(
                          color: Colors.black,
                          fontSize: 18,
                          fontFamily: 'Inter',
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      const SizedBox(height: 12),
                      _buildCareGuideContent(widget.item.careGuide),
                    ],
                  ),
                ),
              const SizedBox(height: 24),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildCareGuideContent(Map<String, dynamic>? careGuide) {
    if (careGuide == null || careGuide.isEmpty) {
      return const Text(
        'No care guidance available',
        style: TextStyle(
          color: Colors.grey,
          fontSize: 14,
          fontFamily: 'Inter',
        ),
      );
    }

    final StringBuffer sb = StringBuffer();
    careGuide.forEach((key, value) {
      sb.writeln('$key: $value');
    });

    return Text(
      sb.toString().trim(),
      style: const TextStyle(
        color: Colors.black,
        fontSize: 14,
        fontFamily: 'Inter',
        fontWeight: FontWeight.w400,
        height: 1.6,
      ),
    );
  }
}